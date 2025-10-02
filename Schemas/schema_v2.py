from pydantic import BaseModel, Field, UUID4
from datetime import datetime
from typing import Optional, List
from enum import Enum
from decimal import Decimal

# Assuming db_config is in a file you manage
# from db_config.db_config import read_db_config
# db_param = read_db_config()
# Pydantic v2 now uses from_attributes=True instead of orm_mode=True
# All models below use this, so you can remove the old `orm_mode = True` and `from_attributes = True` lines.

class SignUpModel(BaseModel):
    id: Optional[UUID4] = None
    username: str
    email: str
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    is_staff: Optional[bool] = False
    is_active: Optional[bool] = False

    class Config:
        json_schema_extra = {
            "example": {
                "username": "john_doe",
                "email": "john_doe@gmail.com",
                "password": "securepassword123",
                "first_name": "John",
                "last_name": "Doe",
                "phone_number": "08012345678",
                "is_staff": False,
                "is_active": True
            }
        }

class AddressType(str, Enum):
    HOME = "HOME"
    WORK = "WORK"
    OTHER = "OTHER"

class AddressUpdateModel(BaseModel):
    address_type: AddressType = AddressType.HOME
    recipient_name: Optional[str] = None
    street_address1: str
    street_address2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    is_default: bool

class AddressResponseModel(BaseModel):
    address_type: AddressType = AddressType.HOME
    street_address1: Optional[str]
    street_address2: Optional[str]
    postal_code: Optional[str]
    city: Optional[str]
    state: Optional[str]
    country: Optional[str]
    full_address: Optional[str]
    is_default: Optional[bool]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class UserUpdateModel(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "first_name": "Jane",
                "last_name": "Doe",
                "phone_number": "+2348012345678"
            }
        }

class UserResponseModel(BaseModel):
    username: Optional[str]
    email: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    phone_number: Optional[str]
    is_staff: Optional[bool]
    is_active: Optional[bool]
    full_address: Optional[str]
    updated_at: datetime

    class Config:
        from_attributes = True

class UserListResponseModel(BaseModel):
    message: str
    users: List[UserResponseModel]

class CategoryBase(BaseModel):
    name: str = Field(..., max_length=50)
    description: Optional[str] = None
    parent_id: Optional[UUID4] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(CategoryBase):
    name: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    parent_id: Optional[UUID4] = None

class CategoryResponse(CategoryBase):
    name: str = Field(..., max_length=50)
    description: Optional[str] = None
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class ProductBase(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    base_price: Decimal = Field(..., ge=Decimal(0))
    category_id: UUID4
    is_active: bool = True
    image_url: Optional[str] = Field(None, max_length=255)

class ProductCreate(ProductBase):
    pass

class ProductUpdate(ProductBase):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    base_price: Optional[Decimal] = Field(None, ge=Decimal(0))
    category_id: Optional[UUID4] = None
    is_active: Optional[bool] = None
    image_url: Optional[str] = Field(None, max_length=255)

class ProductResponse(ProductBase):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    base_price: Optional[Decimal] = Field(None, ge=Decimal(0))
    category: Optional[CategoryResponse] = None
    is_active: Optional[bool] = None
    image_url: Optional[str] = Field(None, max_length=255)
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class ProductVariantBase(BaseModel):
    product_id: UUID4
    name: str = Field(..., max_length=50)
    price_modifier: Decimal = Field(Decimal(0.00), ge=Decimal(0))
    sku: Optional[str] = Field(None, max_length=50)

class ProductVariantCreate(ProductVariantBase):
    pass

class ProductVariantUpdate(ProductVariantBase):
    product_id: Optional[UUID4] = None
    name: Optional[str] = Field(None, max_length=50)
    price_modifier: Optional[Decimal] = Field(None, ge=Decimal(0))
    sku: Optional[str] = Field(None, max_length=50)

class ProductVariantResponse(ProductVariantBase):
    id: UUID4
    created_at: datetime
    updated_at: datetime
    product: Optional[ProductResponse] = None

    class Config:
        from_attributes = True

class Settings(BaseModel):
    # This class should be refactored to use environment variables for secret keys
    authjwt_secret_key: str = "your-secret-key-here"  # Hardcoded for example, use a more secure method
    authjwt_algorithm: str = "HS256"
    authjwt_access_token_expires: int = 900
    authjwt_refresh_token_expires: int = 86400
    authjwt_token_location: set = {"headers", "cookies"}
    authjwt_cookie_secure: bool = False
    authjwt_cookie_samesite: str = "lax"
    authjwt_cookie_path: str = "/"
    authjwt_cookie_domain: Optional[str] = None

class LoginModel(BaseModel):
    username: str
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "username": "john_doe",
                "password": "securepassword123"
            }
        }

# --- New/Corrected Order Schemas ---
# Schemas for Order Creation
class OrderItemCreateModel(BaseModel):
    product_id: UUID4
    variant_id: Optional[UUID4] = None
    quantity: int = Field(..., gt=0, description="The quantity must be a positive integer")

class OrderCreateModel(BaseModel):
    delivery_address_id: UUID4
    items: List[OrderItemCreateModel]

# Schemas for API Responses
class OrderItemResponseModel(BaseModel):
    product_name: str
    variant_name: Optional[str] = None
    quantity: int
    unit_price: Decimal

    class Config:
        from_attributes = True

class OrderResponseModel(BaseModel):
    order_id: UUID4
    total_amount: Decimal
    order_status: str
    delivery_address_id: UUID4
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemResponseModel]

    class Config:
        from_attributes = True

class OrderListResponseModel(BaseModel):
    message: str
    orders: List[OrderResponseModel]

class OrderStatusUpdateModel(BaseModel):
    order_status: str

    class Config:
        from_attributes = True