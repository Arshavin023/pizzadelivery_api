from fastapi import APIRouter, status, Depends
from fastapi_jwt_auth import AuthJWT
from typing import List
from models import User, Category, Product, ProductVariant
from schemas import (ProductCreate, ProductUpdate, ProductResponse, ProductVariantCreate, 
                     ProductVariantUpdate, ProductVariantResponse)

from database_connection.database import get_async_db  # <-- updated import
from fastapi.exceptions import HTTPException
from fastapi_jwt_auth.exceptions import (
    MissingTokenError,
    InvalidHeaderError,
    RevokedTokenError,
    AccessTokenRequired,
    JWTDecodeError
)
from fastapi.encoders import jsonable_encoder
from datetime import datetime
from uuid import UUID 
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from redis_blacklist import add_token_to_blocklist, is_token_blocklisted
from sqlalchemy.orm import selectinload

# --- FastAPI Routers ---
product_router = APIRouter()
product_variant_router = APIRouter()

async def require_jwt(Authorize: AuthJWT = Depends()):
    try:
        Authorize.jwt_required()
        raw_token = Authorize.get_raw_jwt()['jti']
        if is_token_blocklisted(raw_token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
    except MissingTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization token is missing")
    except InvalidHeaderError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid JWT header format")
    except JWTDecodeError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired JWT token")
    except RevokedTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked")
    except AccessTokenRequired:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token is required")
    
    return Authorize.get_jwt_subject()

@product_router.get("/")
async def hello(Authorize: AuthJWT = Depends()):
    """
        ## A sample route to test JWT authentication.
        This route requires a valid JWT token to access.
        It returns a simple message "Hello World" if the token is valid.
        ### JWT Authentication Required
        - The JWT token must be included in the request header as `Authorization    Bearer <token>`.      
    """
    await require_jwt(Authorize)
    return {"message": "Hello World"}

# --- Product Routes ---
@product_router.post("/create/", response_model=ProductResponse, 
                     status_code=status.HTTP_201_CREATED)
async def create_product(product_data: ProductCreate, 
                         Authorize: AuthJWT = Depends(),
                         db: AsyncSession = Depends(get_async_db)):
    """
    ## Create Product
    This route allows you to create a new product.
    A valid `category_id` must be provided.
    """
    current_user = await require_jwt(Authorize)
    async with db.begin():
        result = await db.execute(
            select(User.is_staff).where(User.username == current_user)
        )
        user_row = result.first()

        if not user_row or not user_row.is_staff:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource"
            )
        # Verify category_id exists
        category_result = await db.execute(
            select(Category).where(Category.id == product_data.category_id)
        )
        category = category_result.scalar_one_or_none()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found for the given category_id."
            )

        #  Check for unique product name
        existing_product_name = await db.execute(
            select(Product).where(Product.name.ilike(product_data.name))
        )
        if existing_product_name.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Product with this name already exists."
            )

        new_product = Product(**product_data.dict())
        db.add(new_product)
        await db.flush()
        # Load the category relationship for the response
        await db.refresh(new_product, attribute_names=["category"])
        return ProductResponse.from_orm(new_product)

@product_router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: UUID, 
                      Authorize: AuthJWT = Depends(),
                      db: AsyncSession = Depends(get_async_db)):
    """
    ## Get Product by ID
    This route retrieves a single product by its ID, including its associated category.
    """
    await require_jwt(Authorize)
    
    product_result = await db.execute(
        select(Product)
            .options(selectinload(Product.category))  #eager-load category
            .where(Product.id == product_id)
        )

    product = product_result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Product not found")
    return ProductResponse.from_orm(product)

@product_router.get("/products/", response_model=List[ProductResponse])
async def get_all_products(
    Authorize: AuthJWT = Depends(),
    db: AsyncSession = Depends(get_async_db)):
    """
    ## Get All Products
    This route retrieves a list of all products, including their associated categories.
    """
    await require_jwt(Authorize)
    # products_result = await db.execute(select(Product))
    # products = products_result.scalars().all()

    products_result = await db.execute(
        select(Product).options(selectinload(Product.category))
    )
    products = products_result.scalars().all()
    return products

@product_router.put("/update/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: UUID, 
    product_update: ProductUpdate, 
    Authorize: AuthJWT = Depends(),
    db: AsyncSession = Depends(get_async_db)
):
    """
    ## Update Product
    This route updates an existing product by its ID.
    If `category_id` is provided, it will be validated.
    """
    current_user=await require_jwt(Authorize)
    async with db.begin():
        result = await db.execute(
            select(User.is_staff).where(User.username == current_user)
        )
        user_row = result.first()

        if not user_row or not user_row.is_staff:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource"
            )
        
        product_result = await db.execute(
            select(Product)
            .options(selectinload(Product.category))  # 👈 Load category eagerly
            .where(Product.id == product_id)
        )

        product = product_result.scalar_one_or_none()

        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

        # If category_id is provided in update, verify it exists
        if product_update.category_id and product_update.category_id != product.category_id:
            category_result = await db.execute(
                select(Category).where(Category.id == product_update.category_id)
            )
            category = category_result.scalar_one_or_none()
            if not category:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="New category_id not found."
                )

        update_data = product_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(product, field, value)
        await db.commit() 

    await db.refresh(product)
    return ProductResponse.from_orm(product)

@product_router.delete("/delete/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(product_id: UUID, 
                         Authorize: AuthJWT = Depends(),
                         db: AsyncSession = Depends(get_async_db)):
    """
    ## Delete Product
    This route deletes a product by its ID.
    Due to `cascade='all, delete-orphan'` on `Product.variants`, deleting a product will
    automatically delete all its associated product variants.
    """
    current_user = await require_jwt(Authorize)
    async with db.begin():
        result = await db.execute(
            select(User.is_staff).where(User.username == current_user)
        )
        user_row = result.first()

        if not user_row or not user_row.is_staff:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource"
            )
        
        product_result = await db.execute(
            select(Product).where(Product.id == product_id)
        )
        product = product_result.scalar_one_or_none()

        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

        await db.delete(product)
        # No explicit commit needed here, db.begin() handles it on exit

# --- Product Variant Routes ---
@product_variant_router.post("/", response_model=ProductVariantResponse, 
                             status_code=status.HTTP_201_CREATED)
async def create_product_variant(variant_data: ProductVariantCreate, 
                                 Authorize: AuthJWT = Depends(),
                                 db: AsyncSession = Depends(get_async_db)):
    """
    ## Create Product Variant
    This route allows you to create a new product variant.
    A valid `product_id` must be provided.
    """
    current_user = await require_jwt(Authorize)
    async with db.begin():
        result = await db.execute(
            select(User.is_staff).where(User.username == current_user)
        )
        user_row = result.first()

        if not user_row or not user_row.is_staff:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource"
            )
        
        # Verify product_id exists
        product_result = await db.execute(
            select(Product).where(Product.id == variant_data.product_id)
        )
        product = product_result.scalar_one_or_none()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found for the given product_id."
            )

        # Check for unique SKU
        existing_variant_result = await db.execute(
            select(ProductVariant).where(ProductVariant.sku == variant_data.sku)
        )
        if existing_variant_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Product variant with this SKU already exists."
            )

        new_variant = ProductVariant(**variant_data.dict())
        db.add(new_variant)
        await db.flush()
        # Load the product relationship for the response
        await db.refresh(new_variant, attribute_names=["product"])
        return new_variant

@product_variant_router.get("/{variant_id}", response_model=ProductVariantResponse)
async def get_product_variant(variant_id: UUID, db: AsyncSession = Depends(get_async_db)):
    """
    ## Get Product Variant by ID
    This route retrieves a single product variant by its ID, including its associated product.
    """
    variant_result = await db.execute(
        select(ProductVariant).options(selectinload(ProductVariant.product).selectinload(Product.category)).where(ProductVariant.id == variant_id)
    )
    variant = variant_result.scalar_one_or_none()
    if not variant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product variant not found")
    return variant

@product_variant_router.get("/", response_model=List[ProductVariantResponse])
async def get_all_product_variants(db: AsyncSession = Depends(get_async_db)):
    """
    ## Get All Product Variants
    This route retrieves a list of all product variants, including their associated products.
    """
    variants_result = await db.execute(
        select(ProductVariant).options(selectinload(ProductVariant.product).selectinload(Product.category))
    )
    variants = variants_result.scalars().all()
    return variants

@product_variant_router.put("/{variant_id}", response_model=ProductVariantResponse)
async def update_product_variant(
    variant_id: UUID, variant_update: ProductVariantUpdate, db: AsyncSession = Depends(get_async_db)
):
    """
    ## Update Product Variant
    This route updates an existing product variant by its ID.
    If `product_id` is provided, it will be validated.
    """
    async with db.begin():
        variant_result = await db.execute(
            select(ProductVariant).where(ProductVariant.id == variant_id)
        )
        variant = variant_result.scalar_one_or_none()

        if not variant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product variant not found")

        # If product_id is provided in update, verify it exists
        if variant_update.product_id and variant_update.product_id != variant.product_id:
            product_result = await db.execute(
                select(Product).where(Product.id == variant_update.product_id)
            )
            product = product_result.scalar_one_or_none()
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="New product_id not found."
                )
        
        # Check for unique SKU if SKU is provided and different
        if variant_update.sku and variant_update.sku != variant.sku:
            existing_variant_result = await db.execute(
                select(ProductVariant).where(ProductVariant.sku == variant_update.sku)
            )
            if existing_variant_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Product variant with this SKU already exists."
                )

        update_data = variant_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(variant, field, value)

        await db.refresh(variant, attribute_names=["product"]) # Refresh with product for response
        return variant

@product_variant_router.delete("/{variant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product_variant(variant_id: UUID, db: AsyncSession = Depends(get_async_db)):
    """
    ## Delete Product Variant
    This route deletes a product variant by its ID.
    """
    async with db.begin():
        variant_result = await db.execute(
            select(ProductVariant).where(ProductVariant.id == variant_id)
        )
        variant = variant_result.scalar_one_or_none()

        if not variant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product variant not found")

        await db.delete(variant)
        # No explicit commit needed here, db.begin() handles it on exit