from fastapi import APIRouter, status, Depends
from fastapi_jwt_auth import AuthJWT
from typing import List
from models import User, Category, Product, ProductVariant
from schemas import (CategoryCreate, CategoryUpdate, CategoryResponse,
                     ProductCreate, ProductUpdate, ProductResponse, ProductVariantCreate, 
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


# --- FastAPI Routers ---
category_router = APIRouter(prefix="/categories", tags=["Categories"])
product_router = APIRouter(prefix="/products", tags=["Products"])
product_variant_router = APIRouter(prefix="/product_variants", tags=["Product Variants"])

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

# --- Category Routes ---
@category_router.post("/create/", response_model=CategoryResponse, 
                      status_code=status.HTTP_201_CREATED)
async def create_category(category_data: CategoryCreate, 
                          Authorize: AuthJWT = Depends(),
                          db: AsyncSession = Depends(get_async_db)):
    """
    ## Create Category
    This route allows you to create a new category.
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
        
        # Check for unique name
        existing_category_name = await db.execute(
            select(Category).where(Category.name.ilike(category_data.name))
        )
        if existing_category_name.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Category with this name already exists."
            )

        new_category = Category(**category_data.dict())
        db.add(new_category)
        await db.commit() # Commit the transaction to save the new category
        return new_category

@category_router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(category_id: UUID, 
                       Authorize: AuthJWT = Depends(),
                       db: AsyncSession = Depends(get_async_db)):
    """
    ## Get Category by ID
    This route retrieves a single category by its ID.
    """
    await require_jwt(Authorize)
    category_result = await db.execute(
        select(Category).where(Category.id == category_id)
    )
    category = category_result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    # return CategoryResponse.from_orm(category)
    return category

@category_router.get("/", response_model=List[CategoryResponse])
async def get_all_categories(
    Authorize: AuthJWT = Depends(),
    db: AsyncSession = Depends(get_async_db)):
    """
    ## Get All Categories
    This route retrieves a list of all categories.
    """
    await require_jwt(Authorize)
    categories_result = await db.execute(select(Category))
    categories = categories_result.scalars().all()
    return categories

@category_router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: UUID, 
    category_update: CategoryUpdate, 
    Authorize: AuthJWT = Depends(),
    db: AsyncSession = Depends(get_async_db)
    ):
    """
    ## Update Category
    This route updates an existing category by its ID.
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
        
        category_result = await db.execute(
            select(Category).where(Category.id == category_id)
        )
        category = category_result.scalar_one_or_none()

        if not category:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

        update_data = category_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(category, field, value)

        await db.refresh(category)
        return category

@category_router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(category_id: UUID, 
                          Authorize: AuthJWT = Depends(),
                          db: AsyncSession = Depends(get_async_db)):
    """
    ## Delete Category
    This route deletes a category by its ID.
    Note: Deleting a category will also delete associated products and product variants
    if ON DELETE CASCADE is configured in your database for the foreign key.
    SQLAlchemy's `cascade='all, delete-orphan'` on `Product.variants` means deleting a Product
    deletes its variants. Deleting a Category does NOT automatically delete Products
    unless your database foreign key constraint is set to `ON DELETE CASCADE`.
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
        
        category_result = await db.execute(
            select(Category).where(Category.id == category_id)
        )
        category = category_result.scalar_one_or_none()

        if not category:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

        await db.delete(category)
        # No explicit commit needed here, db.begin() handles it on exit

# --- Product Routes ---
@product_router.post("/{category_id}", response_model=ProductResponse, 
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

        new_product = Product(**product_data.dict())
        db.add(new_product)
        await db.flush()
        # Load the category relationship for the response
        await db.refresh(new_product, attribute_names=["category"])
        return new_product

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
        select(Product).where(Product.id == product_id)
    )

    # product_result = await db.execute(
    #     select(Product).options(selectinload(Product.category)).where(Product.id == product_id)
    # )
    product = product_result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                            detail="Product not found")
    return product

@product_router.get("/", response_model=List[ProductResponse])
async def get_all_products(
    Authorize: AuthJWT = Depends(),
    db: AsyncSession = Depends(get_async_db)):
    """
    ## Get All Products
    This route retrieves a list of all products, including their associated categories.
    """
    await require_jwt(Authorize)
    products_result = await db.execute(select(Product))
    products = products_result.scalars().all()

    # products_result = await db.execute(
    #     select(Product).options(selectinload(Product.category))
    # )
    # products = products_result.scalars().all()
    return products

@product_router.put("/{product_id}", response_model=ProductResponse)
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
            select(Product).where(Product.id == product_id)
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

        await db.refresh(product, attribute_names=["category"]) # Refresh with category for response
        return product

@product_router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
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