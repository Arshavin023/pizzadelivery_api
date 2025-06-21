from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID 
from db_config.db_config import read_db_config
from fastapi_jwt_auth import AuthJWT

db_param = read_db_config()

class SignUpModel(BaseModel):
    """User Registration Model
    This model is used for user registration, capturing all necessary user details.
    Attributes:
        id (Optional[UUID]): Unique identifier for the user.
        username (str): Unique username for the user.
        email (str): User's email address.
        password (str): User's password (should be hashed before storage).
        first_name (Optional[str]): User's first name.
        last_name (Optional[str]): User's last name.
        address (Optional[str]): User's address.
        state (Optional[str]): User's state of residence.
        local_government (Optional[str]): User's local government area.
        phone_number (Optional[str]): User's phone number.
        is_staff (Optional[bool]): Indicates if the user is a staff member (default is False).
        is_active (Optional[bool]): Indicates if the user account is active (default is False).
    This model is used to create a new user in the system.
    It includes fields for all necessary user information and provides an example for reference.
    The `Config` class includes settings for JSON schema generation and example data.       
    """
    id:Optional[UUID]
    username:str
    email:str
    password:str
    first_name:Optional[str]
    last_name:Optional[str] 
    address:Optional[str]
    state:Optional[str] 
    local_government:Optional[str] 
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
                "address": "2 Nwodo Street, Owerri Municipal",
                "state": "Imo",
                "local_government": "Owerri Municipal",
                "phone_number": "08012345678",
                "is_staff": False,
                "is_active": True
            }
            }
        
class UserUpdateModel(BaseModel):
    """User Update Model
    This model is used for updating user information, capturing all necessary fields that can be modified.
    Attributes:
        first_name (Optional[str]): User's first name.
        last_name (Optional[str]): User's last name.
        address (Optional[str]): User's address.
        state (Optional[str]): User's state of residence.
        local_government (Optional[str]): User's local government area.
        phone_number (Optional[str]): User's phone number.
    This model is used to update existing user information in the system.
    It includes fields for all necessary user information and provides an example for reference.
    The `Config` class includes settings for JSON schema generation and example data."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    address: Optional[str] = None
    state: Optional[str] = None
    local_government: Optional[str] = None
    phone_number: Optional[str] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "first_name": "Jane",
                "last_name": "Doe",
                "address": "123 Main St, Springfield",
                "state": "Illinois",
                "local_government": "Springfield",
                "phone_number": "123-456-7890"
            }
        }

class UserResponseModel(BaseModel):
    """User Response Model
    This model is used to represent the user information returned in API responses.
    Attributes:
        id (UUID): Unique identifier for the user.
        username (str): Unique username for the user.
        email (str): User's email address.
        first_name (Optional[str]): User's first name.
        last_name (Optional[str]): User's last name.
        address (Optional[str]): User's address.
        state (Optional[str]): User's state of residence.
        local_government (Optional[str]): User's local government area.
        phone_number (Optional[str]): User's phone number.
        time_created (datetime): Timestamp when the user was created.
        is_staff (bool): Indicates if the user is a staff member.
        is_active (bool): Indicates if the user account is active.
    This model is used to return user information in API responses.
    It includes fields for all necessary user information and provides an example for reference.
    The `Config` class includes settings for ORM compatibility and JSON schema generation.  
    """
    id: UUID
    username: str
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    address: Optional[str]
    state: Optional[str]
    local_government: Optional[str]
    phone_number: Optional[str]
    time_created: datetime
    is_staff: bool
    is_active: bool

    class Config:
        from_attributes = True  # For ORM compatibility (Pydantic v2+)
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

class OrderModel(BaseModel):
    """
    Order Model
    This model is used to create a new order, capturing all necessary order details.
    Attributes:
        id (Optional[UUID]): Unique identifier for the order.
        quantity (int): The quantity of pizzas ordered.
        order_status (Optional[str]): 
            The status of the order (e.g., "PENDING", "DELIVERED", "CANCELLED").
        pizza_size (Optional[str]): The size of the pizza (e.g., "SMALL", "MEDIUM", "LARGE").
        flavour (Optional[str]): The flavour of the pizza (e.g., "PEPPERONI", "MARGHERITA").
        user_id (Optional[UUID]): Unique identifier for the user placing the order.
        total_cost (Optional[float]): The total cost of the order.
        time_created (Optional[datetime]): Timestamp when the order was created (default is current time).
    This model is used to create a new order in the system.
    It includes fields for all necessary order information and provides an example for reference.
    The `Config` class includes settings for ORM compatibility and JSON schema generation.         
    """
    id:Optional[UUID]
    quantity:int
    order_status:Optional[str]
    pizza_size: Optional[str]
    flavour:Optional[str]
    user_id:Optional[UUID]
    total_cost:Optional[float] 
    time_created:Optional[datetime] = datetime.now()

    class Config:
        orm_mode = True
        from_attributes = True
        json_schema_extra = {
            "example": {
                "quantity": 2,
                "pizza_size": "MEDIUM",
                "flavour": "PEPPERONI"
                    }
        }

class OrderStatusUpdateModel(BaseModel):
    """
    Order Status Update Model
    This model is used to update the status of an existing order.
    Attributes:
        order_status (Optional[str]): 
            The new status of the order (e.g., "PENDING", "DELIVERED", "CANCELLED").
    This model is used to update the status of an existing order in the system.
    It includes a field for the new order status and provides an example for reference.
    The `Config` class includes settings for ORM compatibility and JSON schema generation.  
    """
    order_status: Optional[str] = "PENDING"

    class Config:
        from_attributes = True
        orm_mode = True
        json_schema_extra = {
            "example": {
                "order_status": "DELIVERED"
            }
        }

class OrderResponseModel(BaseModel):
    """
    Order Response Model
    This model is used to represent the order information returned in API responses.
    Attributes:
        message (Optional[str]): A message related to the order (e.g., success or error message).
        order_id (Optional[UUID]): Unique identifier for the order.
        pizza_size (Optional[str]): The size of the pizza ordered.
        quantity (Optional[int]): The quantity of pizzas ordered.
        order_status (Optional[str]): The status of the order (e.g., "PENDING", "DELIVERED", "CANCELLED").
        flavour (Optional[str]): The flavour of the pizza ordered.
        total_cost (Optional[float]): The total cost of the order.
        time_created (datetime): Timestamp when the order was created.
    This model is used to return order information in API responses.
    It includes fields for all necessary order information and provides an example for reference.
    The `Config` class includes settings for ORM compatibility and JSON schema generation.
    """
    message: Optional[str] 
    order_id: Optional[UUID]
    pizza_size: Optional[str]
    quantity: Optional[int]
    order_status: Optional[str]
    flavour: Optional[str]
    total_cost: Optional[float] = 0.0
    order_status: Optional[str]
    time_created: datetime

    class Config:
        from_attributes = True  # For ORM compatibility (Pydantic v2+)
        orm_mode = True 

# class TokenResponseModel(BaseModel):
#     access_token: str
#     refresh_token: str

#     class Config:
#         from_attributes = True
#         json_schema_extra = {
#             "example": {
#                 "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
#                 "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
#             }
#         }
# class TokenData(BaseModel):
#     username: str
#     is_staff: bool
#     is_active: bool

#     class Config:
#         from_attributes = True
#         json_schema_extra = {
#             "example": {
#                 "username": "john_doe",
#                 "is_staff": False,
#                 "is_active": True
#             }
#         }
# class RefreshTokenModel(BaseModel):
#     refresh_token: str

#     class Config:
#         from_attributes = True
#         json_schema_extra = {
#             "example": {
#                 "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
#             }
#         }