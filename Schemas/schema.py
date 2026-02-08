from pydantic import BaseModel, Field, UUID4, ConfigDict
from datetime import datetime
from typing import Optional, List
from enum import Enum
from decimal import Decimal
from db_config.db_config import read_db_config

# Ensure you have installed fastapi-jwt-auth2
from fastapi_jwt_auth2 import AuthJWT

db_param = read_db_config()

class SignUpModel(BaseModel):
    username: str
    email: str
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None 
    phone_number: Optional[str] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "username": "john_doe",
                "email": "john_doe@gmail.com",
                "password": "securepassword123",
                "first_name": "John",
                "last_name": "Doe",
                "phone_number": "08012345678"
            }
        }
    )

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
    street_address1: Optional[str] = None
    street_address2: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    full_address: Optional[str] = None
    is_default: Optional[bool] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class UserUpdateModel(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "first_name": "Jane",
                "last_name": "Doe",
                "phone_number": "+2348012345678"
            }
        }
    )

class UserResponseModel(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    is_staff: Optional[bool] = None
    is_active: Optional[bool] = None
    full_address: Optional[str] = None 
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class UserListResponseModel(BaseModel):
    message: str
    users: List[UserResponseModel]

class CategoryBase(BaseModel):
    name: str = Field(..., max_length=50)
    description: Optional[str] = None

class CategoryResponse(CategoryBase):
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class ProductBase(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None

class ProductResponse(ProductBase):
    category: Optional[CategoryResponse] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class ProductVariantResponse(BaseModel):
    id: UUID4
    product_id: UUID4
    name: str
    price_modifier: float
    sku: Optional[str]
    created_at: datetime
    updated_at: datetime
    product: Optional[ProductResponse] = None

    model_config = ConfigDict(from_attributes=True)

class Settings(BaseModel):
    authjwt_secret_key: str = db_param['jwt_token']
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

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "username": "john_doe",
                "password": "securepassword123"
            }
        }
    )

class OrderItemResponseModel(BaseModel):
    product_name: str
    variant_name: Optional[str] = None
    quantity: int
    unit_price: Decimal
    model_config = ConfigDict(from_attributes=True)

class OrderResponseModel(BaseModel):
    order_id: UUID4
    total_amount: Decimal
    order_status: str
    delivery_address_id: UUID4
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemResponseModel]
    model_config = ConfigDict(from_attributes=True)