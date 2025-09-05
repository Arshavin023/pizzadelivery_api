from fastapi import APIRouter, status, Depends
from fastapi_jwt_auth import AuthJWT
from typing import List
from models import User, Category, Product, ProductVariant
from schemas import (CategoryCreate, CategoryUpdate, CategoryResponse)
from database_connection.database import get_async_db  # <-- updated import
from fastapi.exceptions import HTTPException
from auth_routes import require_jwt
from fastapi.encoders import jsonable_encoder
from datetime import datetime
from uuid import UUID 
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from redis_blacklist import add_token_to_blocklist, is_token_blocklisted


# --- FastAPI Routers ---
category_router = APIRouter()

@category_router.get("/")
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
# Create a new category
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
    return CategoryResponse.from_orm(new_category)

# Get a category by ID
@category_router.get("/retrieve/{category_id}", response_model=CategoryResponse)
async def get_category(category_id: UUID, 
                       Authorize: AuthJWT = Depends(),
                       db: AsyncSession = Depends(get_async_db)):
    """
    ## Get Category by ID
    This route retrieves a single category by its ID.
    """
    # await require_jwt(Authorize)
    category_result = await db.execute(
        select(Category).where(Category.id == category_id)
    )
    category = category_result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return CategoryResponse.from_orm(category)
    # return category

@category_router.get("/categories/", response_model=List[CategoryResponse])
async def get_all_categories(
    Authorize: AuthJWT = Depends(),
    db: AsyncSession = Depends(get_async_db)):
    """
    ## Get All Categories
    This route retrieves a list of all categories.
    """
    # await require_jwt(Authorize)
    categories_result = await db.execute(select(Category))
    categories = categories_result.scalars().all()
    return categories

@category_router.put("/update/{category_id}", response_model=CategoryResponse)
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
        # Check for unique name
        existing_category_name = await db.execute(
            select(Category).where(
                Category.name.ilike(category_update.name) & 
                (Category.id != category_id)
            )
        )
        if existing_category_name.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Category with this name already exists."
            )
        
        # Update the category fields
        update_data = category_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(category, field, value)
        await db.commit() # Commit the transaction to save the new category
    
    await db.refresh(category)
    return CategoryResponse.from_orm(category)

@category_router.delete("/delete/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
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
