from pydantic import BaseModel, Field, UUID4
from datetime import datetime
from typing import Optional
from db_config.db_config import read_db_config
from fastapi_jwt_auth import AuthJWT
from typing import List
from enum import Enum
from decimal import Decimal

db_param = read_db_config()

class SignUpModel(BaseModel):
    """User Registration Model
    This model is used for user registration, capturing all necessary user details.
    Attributes:
        id (Optional[UUID4]): Unique identifier for the user.
        username (str): Unique username for the user.
        email (str): User's email address.
        password (str): User's password (should be hashed before storage).
        first_name (Optional[str]): User's first name.
        last_name (Optional[str]): User's last name.
        phone_number (Optional[str]): User's phone number.
        is_staff (Optional[bool]): Indicates if the user is a staff member (default is False).
        is_active (Optional[bool]): Indicates if the user account is active (default is False).
    This model is used to create a new user in the system.
    It includes fields for all necessary user information and provides an example for reference.
    The `Config` class includes settings for JSON schema generation and example data.       
    """
    # id:Optional[UUID4]
    username:str
    email:str
    password:str
    first_name:Optional[str]
    last_name:Optional[str] 
    phone_number:Optional[str]
    is_staff:Optional[bool] = False
    is_active:Optional[bool] = False

    class Config:
        from_attributes = True
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
    """AddressType
    This model is used for validating address_type in the AddressUpdateModel 
    and AddressResponseModel
    """
    HOME = "HOME"
    WORK = "WORK"
    OTHER = "OTHER"

class AddressUpdateModel(BaseModel):
    """User Address Update Model
    This model is used for updating user address information, 
    capturing all necessary fields that can be modified.
    Attributes:
        address_type: Home, Work, or Other
        street_address1 (str): Primary street address of the user.
        street_address2 (Optional[str]): Secondary street address of the user (optional).
        postal_code (Optional[str]): Postal code of the user's address.
        city (Optional[str]): City of the user's address.
        state (Optional[str]): State of the user's address.
        country (Optional[str]): Country of the user's address.
        is_default (bool): Indicates if this address is the default address for the user.
    This model is used to update existing user information in the system.
    It includes fields for all necessary user information and provides an example for reference.
    The `Config` class includes settings for JSON schema generation and example data."""
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
        orm_mode = True

class UserUpdateModel(BaseModel):
    """User Update Model
    This model is used for updating user information, capturing all necessary fields that can be modified.
    Attributes:
        first_name (Optional[str]): User's first name.
        last_name (Optional[str]): User's last name.
        phone_number (Optional[str]): User's phone number.
        is_staff (bool): Indicates if the user is a staff member.
        is_active (bool): Indicates if the user account is active.
    This model is used to update existing user information in the system.
    It includes fields for all necessary user information and provides an example for reference.
    The `Config` class includes settings for JSON schema generation and example data."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    # addresses: Optional[List[AddressUpdateModel]] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "first_name": "Jane",
                "last_name": "Doe",
                "phone_number": "+2348012345678"
            }
        }

class UserResponseModel(BaseModel):
    """User Response Model
    This model is used to represent the user information returned in API responses.
    Attributes:
        id (UUID4): Unique identifier for the user.
        username (str): Unique username for the user.
        email (str): User's email address.
        first_name (Optional[str]): User's first name.
        last_name (Optional[str]): User's last name.
        address_type: Home, Work, or Other
        street_address1 (str): Primary street address of the user.
        street_address2 (Optional[str]): Secondary street address of the user (optional).
        postal_code (Optional[str]): Postal code of the user's address.
        city (Optional[str]): City of the user's address.
        state (Optional[str]): State of the user's address.
        country (Optional[str]): Country of the user's address.
        phone_number (Optional[str]): User's phone number.
        updated_at (datetime): Last Timestamp when the user was updated.
        is_staff (bool): Indicates if the user is a staff member.
        is_active (bool): Indicates if the user account is active.
    This model is used to return user information in API responses.
    It includes fields for all necessary user information and provides an example for reference.
    The `Config` class includes settings for ORM compatibility and JSON schema generation.  
    """
    # id: Optional[UUID4]
    username: Optional[str]
    email: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    phone_number: Optional[str]
    is_staff: Optional[bool]
    is_active: Optional[bool]
    full_address: Optional[str]  # from default address only
    # addresses: List[AddressResponseModel] = []
    updated_at: datetime

    class Config:
        from_attributes = True
        orm_mode = True  

class UserListResponseModel(BaseModel):
    message: str
    users: List[UserResponseModel]

class CategoryBase(BaseModel):
    name: str = Field(..., max_length=50)
    description: Optional[str] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(CategoryBase):
    pass
    # name: Optional[str] = Field(None, max_length=50) # Make name optional for updates
    # description: Optional[str] = None
    # parent_id: Optional[UUID4] = None

class CategoryResponse(CategoryBase):
    # name: str = Field(..., max_length=50)
    # description: Optional[str] = None
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True # Enable ORM mode for automatic mapping from SQLAlchemy models

# Product Models
class ProductBase(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None

class ProductCreate(ProductBase):
    base_price: float = Field(..., ge=0) # Using float for Pydantic, will be Numeric in DB
    # category_id: Optional[UUID4]
    is_active: bool = False
    image_url: Optional[str] = Field(None, max_length=255)

class ProductUpdate(ProductBase):
    base_price: float = Field(..., ge=0) # Using float for Pydantic, will be Numeric in DB
    # category_id: Optional[UUID4]
    is_active: bool = False
    image_url: Optional[str] = Field(None, max_length=255)

class ProductResponse(ProductBase):
    category: Optional[CategoryResponse] = None # Include category details in response
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True

# Product Variant Models
class ProductVariantBase(BaseModel):
    product_id: UUID4
    name: str = Field(..., max_length=50)
    price_modifier: float = Field(0.00, ge=0)
    sku: Optional[str] = Field(None, max_length=50)

class ProductVariantCreate(ProductVariantBase):
    pass

class ProductVariantUpdate(ProductVariantBase):
    # product_id: Optional[UUID4] = None
    # name: Optional[str] = Field(None, max_length=50)
    # price_modifier: Optional[float] = Field(None, ge=0)
    sku: Optional[str] = Field(None, max_length=50)

class ProductVariantResponse(ProductVariantBase):
    id: UUID4
    created_at: datetime
    updated_at: datetime
    product: Optional[ProductResponse] = None # Include product details in response

    class Config:
        orm_mode = True

class Settings(BaseModel):
    """Settings Model
    This model is used to configure JWT authentication settings.
    Attributes:
        authjwt_secret_key (str): Secret key used to sign the JWT tokens.
        authjwt_algorithm (str): Algorithm used for signing the JWT tokens (default is "HS256").
        authjwt_access_token_expires (int): Expiration time for access tokens in seconds (default is 900 seconds).
        authjwt_refresh_token_expires (int): Expiration time for refresh tokens in seconds (default is 86400 seconds).
        authjwt_token_location (set): Locations where the token can be found (default includes headers and cookies).
        authjwt_cookie_secure (bool): Whether to use secure cookies (default is False, set to True in production with HTTPS).
        authjwt_cookie_samesite (str): SameSite attribute for cookies (default is "lax").
        authjwt_cookie_path (str): Path for the cookie (default is "/").
        authjwt_cookie_domain (Optional[str]): Domain for the cookie, if needed.
    This model is used to configure JWT authentication settings for the application.
    It includes fields for all necessary JWT settings and provides an example for reference.
    The `Config` class includes settings for JSON schema generation and example data.
    """
    authjwt_secret_key:str = db_param['jwt_token']
    authjwt_algorithm:str = "HS256"
    authjwt_access_token_expires:int = 900  # 1 hour
    authjwt_refresh_token_expires:int = 86400  # 24 hours
    authjwt_token_location: set = {"headers", "cookies"}
    authjwt_cookie_secure: bool = False  # Set to True in production with HTTPS
    authjwt_cookie_samesite: str = "lax"  # Options: "lax", "strict", "none"
    authjwt_cookie_path: str = "/"
    authjwt_cookie_domain: Optional[str] = None  # Set to your domain if needed

class LoginModel(BaseModel):
    """
    Login Model
    This model is used for user login, capturing the necessary credentials.
    Attributes:
        username (str): The username of the user.
        password (str): The password of the user.
    This model is used to authenticate users during login.
    It includes fields for the username and password, and provides an example for reference.
    The `Config` class includes settings for JSON schema generation and example data.
    """
    username: str
    password: str

    class Config:
        from_attributes = True
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