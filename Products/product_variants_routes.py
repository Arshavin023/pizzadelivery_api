from fastapi import APIRouter, status, Depends
from fastapi_jwt_auth import AuthJWT
from typing import List
from Models.models import User, Category, Product, ProductVariant
from Schemas.schemas import (ProductVariantCreate, ProductVariantUpdate, ProductVariantResponse)
from database_connection.database import get_async_db  # <-- updated import
from fastapi.exceptions import HTTPException
from Authentication.auth_routes import require_jwt
from fastapi.encoders import jsonable_encoder
from datetime import datetime
from uuid import UUID 
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from Redis_Caching.redis_blacklist import add_token_to_blocklist, is_token_blocklisted
from sqlalchemy.orm import selectinload
import uuid
from sqlalchemy.exc import IntegrityError


# --- FastAPI Routers ---
product_variants_router = APIRouter()

@product_variants_router.get("/")
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

# --- Product Variant Routes ---
@product_variants_router.post("/create/", response_model=ProductVariantResponse, 
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
        
        # --- FIX: Eagerly load the product's category relationship ---
        # Verify product_id exists
        product_result = await db.execute(
            select(Product).options(selectinload(Product.category)).where(Product.id == variant_data.product_id)
        )
        product = product_result.scalar_one_or_none()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found for the given product_id."
            )

         # --- NEW LOGIC: Check for unique variant name within a product ---
        existing_variant_result = await db.execute(
            select(ProductVariant).where(
                ProductVariant.product_id == variant_data.product_id,
                ProductVariant.name.ilike(variant_data.name)
            )
        )
        if existing_variant_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A variant with the name '{variant_data.name}' already exists for this product."
            )
        
        # --- SKU GENERATION LOGIC ---
        # A good practice is to combine a product identifier with a unique element
        # Here we use the first 8 hex characters of the product's UUID, the variant's name,
        # and the first 6 hex characters of a new UUID to ensure global uniqueness.
        product_prefix = str(variant_data.product_id.hex)[:8]
        variant_name_slug = variant_data.name.replace(" ", "-").upper()
        unique_suffix = uuid.uuid4().hex[:6]
        
        generated_sku = f"{product_prefix}-{variant_name_slug}-{unique_suffix}"
        
        
        # Create a dictionary from the request data and update the sku
        variant_data_dict = variant_data.dict()
        variant_data_dict['sku'] = generated_sku

        new_variant = ProductVariant(**variant_data_dict)
        db.add(new_variant)
        
        try:
            await db.flush()
            # Load the product relationship for the response
            await db.refresh(new_variant, attribute_names=["product"])
            return ProductVariantResponse.from_orm(new_variant)
        except IntegrityError:
            # If a duplicate SKU is somehow generated (extremely rare with this method),
            # this will catch the database error and return a conflict.
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Failed to generate a unique SKU. Please try again."
            )

@product_variants_router.get("/{variant_id}", response_model=ProductVariantResponse)
async def get_product_variant(variant_id: UUID, 
                              db: AsyncSession = Depends(get_async_db)):
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
    
    # Return the variant as a ProductVariantResponse
    return ProductVariantResponse.from_orm(variant)

@product_variants_router.get("/product_variants/", response_model=List[ProductVariantResponse])
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

@product_variants_router.put("/update/{variant_id}", response_model=ProductVariantResponse)
async def update_product_variant(
                                variant_id: UUID, variant_update: ProductVariantUpdate, 
                                Authorize: AuthJWT = Depends(),
                                db: AsyncSession = Depends(get_async_db)
                                ):
    """
    ## Update Product Variant
    This route updates an existing product variant by its ID.
    If `product_id` is provided, it will be validated.
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

        # --- FIX: Eagerly load nested product and category relationships ---
        variant_result = await db.execute(
            select(ProductVariant)
            .options(selectinload(ProductVariant.product)
                     .selectinload(Product.category)
            ).where(ProductVariant.id == variant_id)
        )
        variant = variant_result.scalar_one_or_none()

        if not variant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product variant not found")

        # If product_id is provided in update, verify it exists
        if variant_update.product_id and variant_update.product_id != variant.product_id:
            product_result = await db.execute(
                select(Product).options(selectinload(Product.category)
                                        ).where(Product.id == variant_update.product_id)
            )
            product = product_result.scalar_one_or_none()
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="New product_id not found."
                )
            variant.product = product # Manually set the relationship

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

        # A refresh is not needed here as the relationships are already loaded
        # The ORM will track the changes to the `variant` object automatically
        return ProductVariantResponse.from_orm(variant)

@product_variants_router.delete("/delete/{variant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product_variant(variant_id: UUID,
                                 Authorize: AuthJWT = Depends(),
                                 db: AsyncSession = Depends(get_async_db)):
    """
    ## Delete Product Variant
    This route deletes a product variant by its ID.
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
        variant_result = await db.execute(
            select(ProductVariant).where(ProductVariant.id == variant_id)
        )
        variant = variant_result.scalar_one_or_none()

        if not variant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product variant not found")

        await db.delete(variant)
        # No explicit commit needed here, db.begin() handles it on exit