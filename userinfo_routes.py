from fastapi import APIRouter, status, Depends
from fastapi_jwt_auth import AuthJWT
from models import User
from schemas import UserResponseModel, UserUpdateModel, UserListResponseModel
from database_connection.database import get_async_db  # <-- updated import
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.exceptions import HTTPException
from fastapi.encoders import jsonable_encoder
from datetime import datetime
from sqlalchemy.future import select
import re 

# Add this phone validation pattern
PHONE_REGEX = re.compile(r'^\+?[1-9]\d{1,14}$')  # E.164 format

userinfo_router = APIRouter(
    prefix="/users",
    tags=["users"]
)

async def require_jwt(Authorize: AuthJWT = Depends()):
    try:
        Authorize.jwt_required()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                            detail="Invalid or expired token")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid JWT header"
            )
    return Authorize.get_jwt_subject()

@userinfo_router.get("/")
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

# Get All Users Route SuperAdmin    
@userinfo_router.get("/users/", response_model=UserListResponseModel, 
                     status_code=status.HTTP_200_OK)
async def get_all_users(Authorize: AuthJWT = Depends(), 
                        db: AsyncSession = Depends(get_async_db)
                        ):
    """
    ## Get All Users
    This route retrieves all users in the system.
    Only accessible by users with the `is_staff` role (SuperAdmin).
    ### JWT Authentication Required
    - The JWT token must be included in the request header as `Authorization Bear
    ### Response       
    """
    current_user = await require_jwt(Authorize)
    user = await db.execute(select(User.is_staff).where(User.username == current_user))
    is_staff = user.scalar_one_or_none()
    if not is_staff:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, 
                            detail="You do not have permission to access this resource")
    result = await db.execute(select(User.id,User.email,User.username, User.first_name, User.last_name,
                                   User.address, User.state, User.local_government,
                                   User.phone_number,User.is_active, User.is_staff))
    users = result.fetchall()

    user_lists = [
        UserResponseModel(
            user_id=user.id,
            email=user.email,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            address=user.address,
            state=user.state,
            local_government=user.local_government,
            phone_number=user.phone_number,
            is_active=user.is_active,
            is_staff=user.is_staff
        ) for user in users
        ]

    response =  UserListResponseModel(message="All Users retrieved successfully",
                                           users=user_lists)
    
    return jsonable_encoder(response)

# Get User Info Route
@userinfo_router.get("/info", response_model=UserResponseModel, 
                     status_code=status.HTTP_200_OK)
async def get_user_info(Authorize: AuthJWT = Depends(), 
                        db: AsyncSession = Depends(get_async_db)
                        ):
    """
    ## Get User Information
    This route retrieves the information of the currently authenticated user.
    ### JWT Authentication Required
    - The JWT token must be included in the request header as `Authorization Bearer <token>`.
    ### Response
    - Returns the user's information including `user_id`, `first_name`, `last_name`, `address`, `state`, `local_government`, and `phone_number`.
    """
    current_user = await require_jwt(Authorize)
    user = await db.execute(select(User.id).where(User.username == current_user))
    id = user.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    user = await db.execute(
        select(User.email,User.first_name,User.last_name,User.address,User.state,
               User.local_government,User.phone_number,User.time_created,
               User.is_active,User.is_staff).where(User.id == id)
    )    
    user = user.first()
    response = UserResponseModel(
        email=user.email,
        username=current_user,
        first_name=user.first_name,
        last_name=user.last_name,
        address=user.address,
        state=user.state,
        local_government=user.local_government,
        phone_number=user.phone_number,
        time_created=user.time_created.isoformat() if user.time_created else None,
        is_active=user.is_active, 
        is_staff=user.is_staff  
    )
  
    return jsonable_encoder(response)


# Update User Info Route
@userinfo_router.put("/update", response_model=UserUpdateModel, 
                     status_code=status.HTTP_200_OK)
async def update_user_info(user_update: UserUpdateModel, Authorize: AuthJWT = Depends(), 
                           db: AsyncSession = Depends(get_async_db)):
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
     # Phone validation
    if user_update.phone_number and "+" not in user_update.phone_number:
        raise HTTPException(
            status_code=400,
            detail="Phone number must be in international format (e.g., +1234567890)"
        )
    
    current_user = await require_jwt(Authorize)
    result = await db.execute(select(User).where(User.username == current_user))
    user_to_update = result.scalar_one_or_none()
    if not user_to_update:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Update user fields
    user_to_update.first_name = user_update.first_name
    user_to_update.last_name = user_update.last_name
    user_to_update.address = user_update.address
    user_to_update.state = user_update.state
    user_to_update.local_government = user_update.local_government
    user_to_update.phone_number = user_update.phone_number
    user_to_update.time_created = datetime.now()
    
    await db.commit()
    await db.refresh(user_to_update)
    
    response = UserUpdateModel(
        first_name=user_to_update.first_name,
        last_name=user_to_update.last_name,
        address=user_to_update.address,
        state=user_to_update.state,
        local_government=user_to_update.local_government,
        phone_number=user_to_update.phone_number,
        time_created=user_to_update.time_created.isoformat() if user_to_update.time_created else None
    )

    return jsonable_encoder(response)