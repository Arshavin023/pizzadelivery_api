from fastapi import APIRouter, status, Depends
from sqlalchemy import exists
from sqlalchemy.orm import Session as Session_v2
from schemas import SignUpModel,UserResponseModel,LoginModel
from models import User
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_async_db  # <-- updated import
from fastapi.exceptions import HTTPException
from werkzeug.security import generate_password_hash, check_password_hash
from fastapi_jwt_auth import AuthJWT
from fastapi.encoders import jsonable_encoder
from sqlalchemy.future import select

auth_router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)

# session = Session(bind=engine)

# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

async def require_jwt(Authorize: AuthJWT = Depends()):
    try:
        Authorize.jwt_required()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    return Authorize.get_jwt_subject()

# HomePage Route
@auth_router.get("/")
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

# SignUp Route
@auth_router.post("/signup",response_model=UserResponseModel, 
                  status_code=status.HTTP_201_CREATED)
async def signup(user: SignUpModel,
                 db: AsyncSession = Depends(get_async_db)):
    """
    ## User Registration
    This route allows a new user to register by providing their details.
    ### Request Body
    - `username`: Unique username for the user.
    - `email`: User's email address.
    - `password`: User's password (will be hashed).
    - `first_name`: User's first name.
    - `last_name`: User's last name.
    - `address`: User's address.
    - `state`: User's state.
    - `local_government`: User's local government area.
    - `phone_number`: User's phone number.
    - `is_staff`: Optional, indicates if the user is a staff member (default is False).
    - `is_active`: Optional, indicates if the user account is active (default is False).
    ### Response
    - Returns the created user details.
    ### JWT Authentication Required
    - The JWT token must be included in the request header as `Authorization Bearer <token>`.
    """
    result = await db.execute(select(User.username).where(User.username == user.username))
    db_username = result.scalar_one_or_none()
    if db_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Username already exists"
        )

    # Check if email already exists
    result = await db.execute(select(User).where(User.email == user.email))
    db_email = result.scalar_one_or_none()
    if db_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Email already exists"
        )
    
    new_user = User(
        username=user.username,
        email=user.email,
        password=generate_password_hash(user.password),
        first_name=user.first_name,
        last_name=user.last_name,
        address=user.address,
        state=user.state,
        local_government=user.local_government,
        phone_number=user.phone_number,
        is_staff=user.is_staff,
        is_active=user.is_active
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return UserResponseModel.from_orm(new_user)
    
# Login Route
@auth_router.post("/login")
async def login(user: LoginModel, 
                db: AsyncSession = Depends(get_async_db), 
                Authorize: AuthJWT = Depends()):
    """
    ## User Login
    This route allows a user to log in by providing their username and password.
    ### Request Body
    - `username`: The username of the user.
    - `password`: The password of the user.
    ### Response
    - Returns an access token and a refresh token if the login is successful.
    ### JWT Authentication Required
    - The JWT token must be included in the request header as `Authorization Bearer <token>`.
    """
    
    result = await db.execute(select(User.username, User.password).where(User.username==user.username))
    db_user = result.first()

    # db_user = db.query(User).with_entities(User.username, User.password
    #                                        ).filter_by(username=user.username).first()
    
    if not db_user or not check_password_hash(db_user.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                            detail="Invalid username or password")
    
    access_token = Authorize.create_access_token(subject=db_user.username)
    refresh_token = Authorize.create_refresh_token(subject=db_user.username)
    response = {
        "access": access_token,
        "refresh": refresh_token,
        "token_type": "bearer"
    }
    return jsonable_encoder(response)

# Refresh Token Route
@auth_router.get("/refresh")
async def refresh(Authorize: AuthJWT = Depends()):
    """
    ## Refresh Access Token
    This route allows a user to refresh their access token using a valid refresh token.
    ### JWT Authentication Required
    - The JWT token must be included in the request header as `Authorization Bearer <refresh_token>`.
    ### Response
    - Returns a new access token if the refresh token is valid.
    """
    try:
        Authorize.jwt_refresh_token_required()
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                            detail="Invalid or expired refresh token")
    
    current_user = Authorize.get_jwt_subject()
    new_access_token = Authorize.create_access_token(subject=current_user)
    return jsonable_encoder(
        {"new_access_token": new_access_token, "token_type": "bearer"}
    )