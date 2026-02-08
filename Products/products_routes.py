from fastapi import APIRouter, status, Depends
from fastapi_jwt_auth2 import AuthJWT
from typing import List
from Models.models import User, Category, Product, ProductVariant
from Schemas.schemas_old import (ProductCreate, ProductUpdate, ProductResponse, ProductVariantCreate, 
                     ProductVariantUpdate, ProductVariantResponse)

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
from sqlalchemy.exc import MultipleResultsFound # <--- Import for robustness

# --- FastAPI Routers ---
products_router = APIRouter()

@products_router.get("/")
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
@products_router.post("/create/", response_model=ProductResponse, 
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

@products_router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: str, 
                      db: AsyncSession = Depends(get_async_db)):
    """
    ## Get Product by Name
    This route retrieves a single product by its ID, including its associated category.
    """    
    product_result = await db.execute(
        select(Product)
            .options(selectinload(Product.category))  #eager-load category
            .where(Product.id==product_id)
        )

    product = product_result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Product not found")
    return ProductResponse.from_orm(product)

@products_router.get("/products/", response_model=List[ProductResponse])
async def get_all_products(
    db: AsyncSession = Depends(get_async_db)):
    """
    ## Get All Products
    This route retrieves a list of all products, including their associated categories.
    """
    products_result = await db.execute(
        select(Product).options(selectinload(Product.category))
    )
    products = products_result.scalars().all()
    return products

@products_router.put("/update/{product_id}", response_model=ProductResponse)
async def update_product(
    product_name: str, 
    product_update: ProductUpdate, 
    Authorize: AuthJWT = Depends(),
    db: AsyncSession = Depends(get_async_db)
):
    """
    ## Update Product
    This route updates an existing product by its name.
    If `category_id` is provided, it will be validated.
    """
    search_pattern = f"%{product_name}%"
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
        
        # Eager-load relationships needed by ProductResponse (e.g., Category)
        eager_load_options = [selectinload(Product.category),]

        try:
            # *** FIX APPLIED HERE: Add the eager-loading options ***
            product_result = await db.execute(
                select(Product)
                .options(*eager_load_options) 
                .where(Product.id==product_id)
            )

        # try:
        #     product_result = await db.execute(
        #         select(Product).where(Product.name.ilike(search_pattern))
        #     )
            product = product_result.scalar_one_or_none()
        except MultipleResultsFound:
            # Handle the highly unlikely case where two categories only differ by case
            # (e.g., 'Pizza' and 'pizza' were somehow created)
             raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Multiple categories matching '{product_name}' found. Cannot proceed."
            )
        
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                                detail=f"Product with name {product_name} not found")

        update_data = product_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(product, field, value)
        await db.commit() 

    await db.refresh(product)
    return ProductResponse.from_orm(product)

@products_router.delete("/delete/{product_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(product_name: str, 
                         Authorize: AuthJWT = Depends(),
                         db: AsyncSession = Depends(get_async_db)):
    """
    ## Delete Product
    This route deletes a product by its name.
    Due to `cascade='all, delete-orphan'` on `Product.variants`, deleting a product will
    automatically delete all its associated product variants.
    """
    search_pattern = f"%{product_name}%"
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
        
        try:
            product_result = await db.execute(
                select(Product).where(Product.name.ilike(search_pattern))
            )
            product = product_result.scalar_one_or_none()
        except MultipleResultsFound:
            # Handle the highly unlikely case where two categories only differ by case
            # (e.g., 'Pizza' and 'pizza' were somehow created)
             raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Multiple categories matching '{product_name}' found. Cannot proceed."
            )
        
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                                detail=f"Product with name {product_name} not found")

        await db.delete(product)