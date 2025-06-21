from fastapi import APIRouter, status, Depends
from fastapi_jwt_auth import AuthJWT
from models import User, Order
from schemas import OrderModel,OrderResponseModel, UserResponseModel, UserUpdateModel
from database import engine, SessionLocal #, Session
from sqlalchemy.orm import Session as Session_v2
from fastapi.exceptions import HTTPException
from fastapi.encoders import jsonable_encoder
from datetime import datetime
from uuid import UUID 

userinfo_router = APIRouter(
    prefix="/users",
    tags=["users"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@userinfo_router.get("/")
async def hello(Authorize: AuthJWT = Depends()):
    """
    ## A sample route to test JWT authentication.
    This route requires a valid JWT token to access.
    It returns a simple message "Hello World" if the token is valid.
    ### JWT Authentication Required
    - The JWT token must be included in the request header as `Authorization    Bearer <token>`.      
   """
    try:
        Authorize.jwt_required()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                             detail="Invalid JWT header")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                            detail="Invalid or expired token")
    return {"message": "Hello World"}

# Get All Users Route SuperAdmin    
@userinfo_router.get("/users/", response_model=None, 
                     status_code=status.HTTP_200_OK)
async def get_all_users(Authorize: AuthJWT = Depends(), 
                        db: Session_v2 = Depends(get_db)):
    """
    ## Get All Users
    This route retrieves all users in the system.
    Only accessible by users with the `is_staff` role (SuperAdmin).
    ### JWT Authentication Required
    - The JWT token must be included in the request header as `Authorization Bear
    ### Response       
    """
    try:
        Authorize.jwt_required()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                            detail="Invalid or expired token")
    current_user = Authorize.get_jwt_subject()
    user = db.query(User).with_entities(User.is_staff).filter(User.username == current_user).first()
    if not user.is_staff:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, 
                            detail="You do not have permission to access this resource")
    users = user = db.query(User).with_entities(User.id, User.first_name,User.last_name,User.address,User.state,
                                        User.local_government,User.phone_number).all()

    response = {"message": "SuperAdmin All Users retrieved successfully",
        "users": [
        {
            "user_id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "address": user.address,
            "state": user.state,
            "local_government": user.local_government,
            "phone_number": user.phone_number,
        }
        for user in users]}
    
    return jsonable_encoder(response)

# Get User Info Route
@userinfo_router.get("/info", response_model=None, 
                     status_code=status.HTTP_200_OK)
async def get_user_info(Authorize: AuthJWT = Depends(), 
                        db: Session_v2 = Depends(get_db)):
    """
    ## Get User Information
    This route retrieves the information of the currently authenticated user.
    ### JWT Authentication Required
    - The JWT token must be included in the request header as `Authorization Bearer <token>`.
    ### Response
    - Returns the user's information including `user_id`, `first_name`, `last_name`, `address`, `state`, `local_government`, and `phone_number`.
    """
    try:
        Authorize.jwt_required()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                            detail="Invalid or expired token")
    
    current_user = Authorize.get_jwt_subject()
    user = db.query(User).with_entities(User.id, User.first_name,User.last_name,User.address,User.state,
                                        User.local_government,User.phone_number).filter(User.username == current_user).first()   
    response = {
        "message": "User Information successfully",
        "user_id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "address": user.address,
        "state": user.state,
        "local_government": user.local_government,
        "phone_number": user.phone_number
    }
    return jsonable_encoder(response)

# Update User Info Route
@userinfo_router.put("/update", response_model=None, 
                     status_code=status.HTTP_200_OK)
async def update_user_info(user: UserUpdateModel, Authorize: AuthJWT = Depends(), 
                           db: Session_v2 = Depends(get_db)):
    """
    ## Update User Information
    This route allows the currently authenticated user to update their information.
    ### JWT Authentication Required
    - The JWT token must be included in the request header as `Authorization Bearer <token>`.
    ### Request Body
    - The request body should contain the fields to be updated, such as `first_name`, `last_name`, `address`, `state`, `local_government`, and `phone_number`.
    ### Response
    - Returns a message indicating successful update along with the updated user information.
    """
    try:
        Authorize.jwt_required()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                            detail="Invalid or expired token")
    
    current_user = Authorize.get_jwt_subject()
    existing_user = db.query(User).filter(User.username == current_user).first()
    
    # Update user fields
    existing_user.first_name = user.first_name
    existing_user.last_name = user.last_name
    existing_user.address = user.address
    existing_user.state = user.state
    existing_user.local_government = user.local_government
    existing_user.phone_number = user.phone_number
    
    db.commit()
    
    response = {
        "message": "User Information successfully",
        "first_name": existing_user.first_name,
        "last_name": existing_user.last_name,
        "address": existing_user.address,
        "state": existing_user.state,
        "local_government": existing_user.local_government,
        "phone_number": existing_user.phone_number
    }
    return jsonable_encoder(response)