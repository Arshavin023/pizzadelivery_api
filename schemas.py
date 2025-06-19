from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID 
from db_config.db_config import read_db_config
from fastapi_jwt_auth import AuthJWT

db_param = read_db_config()

class SignUpModel(BaseModel):
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
        
class UserResponseModel(BaseModel):
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
    authjwt_secret_key:str = db_param['jwt_token']
    authjwt_algorithm:str = "HS256"
    authjwt_access_token_expires:int = 900  # 1 hour
    authjwt_refresh_token_expires:int = 86400  # 24 hours
    authjwt_token_location: set = {"headers", "cookies"}
    authjwt_cookie_secure: bool = False  # Set to True in production with HTTPS
    authjwt_cookie_samesite: str = "lax"  # Options: "lax", "strict", "none"
    authjwt_cookie_path: str = "/"
    authjwt_cookie_domain: Optional[str] = None  # Set to your domain if needed

# print(db_param['jwt_token'])

class LoginModel(BaseModel):
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

class OrderResponseModel(BaseModel):
    message: Optional[str] 
    order_id: Optional[UUID]
    pizza_size: Optional[str]
    quantity: int
    flavour: Optional[str]
    total_cost: Optional[float] = 0.0
    order_status: Optional[str]
    time_created: datetime

    class Config:
        from_attributes = True  # For ORM compatibility (Pydantic v2+)
        orm_mode = True 

class TokenResponseModel(BaseModel):
    access_token: str
    refresh_token: str

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }
class TokenData(BaseModel):
    username: str
    is_staff: bool
    is_active: bool

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "username": "john_doe",
                "is_staff": False,
                "is_active": True
            }
        }
class RefreshTokenModel(BaseModel):
    refresh_token: str

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }