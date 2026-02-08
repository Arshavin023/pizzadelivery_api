from fastapi import APIRouter, status, Depends, BackgroundTasks, responses
# from fastapi.responses import RedirectResponse
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from sqlalchemy import exists
from datetime import timedelta, datetime
from sqlalchemy.orm import Session as Session_v2
from Schemas.schemas_old import SignUpModel,UserResponseModel,LoginModel
from Models.models import User, Address
from sqlalchemy.ext.asyncio import AsyncSession
from database_connection.database import get_async_db  # <-- updated import
from fastapi.exceptions import HTTPException
from werkzeug.security import generate_password_hash, check_password_hash
from db_config.db_config import read_db_config
from fastapi_jwt_auth2 import AuthJWT
from fastapi_jwt_auth2.exceptions import (
    MissingTokenError,
    InvalidHeaderError,
    RevokedTokenError,
    AccessTokenRequired,
    JWTDecodeError
)
from fastapi.encoders import jsonable_encoder
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from email_validator import validate_email, EmailNotValidError
import re
from zxcvbn import zxcvbn
from Redis_Caching.redis_blacklist import add_token_to_blocklist, is_token_blocklisted
from jose import jwt, JWTError
from datetime import datetime, timedelta

SECRET_KEY:str = read_db_config()['jwt_token']
ALGORITHM = "HS256"
# Configure your SMTP settings
conf = ConnectionConfig(
    MAIL_USERNAME = "uchejudennodim@gmail.com",
    MAIL_PASSWORD = read_db_config()['google_app_password'],
    MAIL_FROM = "uchejudennodim@gmail.com",
    MAIL_PORT = 587,
    MAIL_SERVER = "smtp.gmail.com",
    MAIL_STARTTLS = True,
    MAIL_SSL_TLS = False,
    USE_CREDENTIALS = True
)

# Add this phone validation pattern
PHONE_REGEX = re.compile(r'^\+?[1-9]\d{1,14}$')  # E.164 format

def is_password_strong(password:str):
    result = zxcvbn(password)
    return result['score'] >= 3  # Require minimum strength score

def create_verification_token(email: str):
    expire = datetime.now() + timedelta(hours=24)
    to_encode = {"exp": expire, "sub": email}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None
    
auth_router = APIRouter()

async def require_jwt(Authorize: AuthJWT = Depends()):
    try:
        Authorize.jwt_required()
        raw_token:str = Authorize.get_raw_jwt()['jti']
        if await is_token_blocklisted(raw_token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token")
        
    except MissingTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization token is missing")
    except InvalidHeaderError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid JWT header format")
    except JWTDecodeError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired JWT token")
    except RevokedTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked")
    except AccessTokenRequired:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token is required")
    
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
@auth_router.post("/register",response_model=None, 
                  status_code=status.HTTP_201_CREATED)
async def signup(user: SignUpModel,
                 background_tasks: BackgroundTasks,
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
    # Email validation
    try:
        valid = validate_email(user.email)
        user.email = valid.email  # Normalized email
    except EmailNotValidError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    # Password validation
    if not is_password_strong(user.password):
        raise HTTPException(
            status_code=400,
            detail="Password is too weak. It must be at least 8 characters long, "
                   "contain a mix of letters, numbers, and symbols, "
                    "and have a strength score of at least 3."
        )
    
    # Phone validation
    if user.phone_number and "+" not in user.phone_number:
        raise HTTPException(
            status_code=400,
            detail="Phone number must be in international format (e.g., +1234567890)"
        )
    
    existing_username = await db.execute(select(User.username).where(User.username == user.username))
    if existing_username.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Username already exists"
        )

    # Check if email already exists
    existing_email = await db.execute(select(User).where(User.email == user.email))
    if existing_email.scalar_one_or_none():
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
        phone_number=user.phone_number
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    token = create_verification_token(user.email)
    verification_url = f"http://localhost:8000/api/auth/verify/{token}"

    # Send Email in Background
    message = MessageSchema(
        subject="Account Verification",
        recipients=[user.email],
        body=f"Click the link to verify your account: {verification_url}",
        subtype="html"
    )
    fm = FastMail(conf)
    background_tasks.add_task(fm.send_message, message)

    return jsonable_encoder({"message": "User created. Please check your email to verify your account."})

# Verify Email Route
@auth_router.get("/verify/{token}")
async def verify_email(token: str, db: AsyncSession = Depends(get_async_db)):
    email = verify_token(token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_active:
        return {"message": "Account already verified"}

    user.is_active = True
    await db.commit()

    return {"message": "Account verified successfully!"}
    
    # Redirect the user to your frontend login page
    # return RedirectResponse(url="https://yourfrontend.com/login?status=success")

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
    
    result = await db.execute(select(User.username, User.password, 
                                     User.is_staff).where(User.username==user.username))
    db_user = result.first()
    
    if not db_user or not check_password_hash(db_user.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                            detail="Invalid username or password")
    
    access_token = Authorize.create_access_token(
        subject=db_user.username,
        expires_time=timedelta(minutes=15),
        user_claims={"is_staff": db_user.is_staff}
        )
    refresh_token = Authorize.create_refresh_token(subject=db_user.username,
                                                   expires_time=timedelta(days=7))
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

# Logout Route
@auth_router.post("/logout")
async def logout(Authorize: AuthJWT = Depends()):
    """
    ## User Logout
    This route allows a user to log out by invalidating their access token.
    ### JWT Authentication Required
    - The JWT token must be included in the request header as `Authorization Bearer <token>`.
    ### Response
    - Returns a success message if the logout is successful.
    """
    try:
        Authorize.jwt_required()
        raw_jwt = Authorize.get_raw_jwt()
        jti = raw_jwt['jti']
        exp_timestamp = raw_jwt['exp']
        expires_in = exp_timestamp - int(datetime.now().timestamp())
        await add_token_to_blocklist(jti, expires_in)
        return {"message": "Logged out successfully"}
    except:
        raise HTTPException(status_code=401, detail="Could not log out.")