from fastapi import APIRouter, status, Depends
from sqlalchemy import exists
from datetime import timedelta, datetime
from sqlalchemy.orm import Session as Session_v2
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from Schemas.schemas import SignUpModel,UserResponseModel,LoginModel
from Models.models import User, Address
from sqlalchemy.ext.asyncio import AsyncSession
from database_connection.database import get_async_db  # <-- updated import
from sqlalchemy.sql import text # <-- Needed for RLS context setup later
from fastapi.exceptions import HTTPException
from werkzeug.security import generate_password_hash, check_password_hash
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import (
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

# Add this phone validation pattern
PHONE_REGEX = re.compile(r'^\+?[1-9]\d{1,14}$')  # E.164 format

def is_password_strong(password:str):
    result = zxcvbn(password)
    return result['score'] >= 3  # Require minimum strength score

auth_router = APIRouter()

async def require_jwt(Authorize: AuthJWT = Depends()):
    try:
        Authorize.jwt_required()
        raw_token = Authorize.get_raw_jwt()['jti']
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
    
    # Extract the tenant_id from the claims
    claims = Authorize.get_raw_jwt()
    tenant_id = claims.get("tenant_id")

    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Tenant information missing from token.")
    
    user_id = Authorize.get_jwt_subject()
    print(user_id, tenant_id)
    
    return user_id, tenant_id
    # try:
    #     # Return both the user ID and the tenant ID (as integers)
    #     return int(user_id), int(tenant_id)
    # except ValueError:
    #     raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
    #                         detail="Invalid ID format in JWT.")
    

# In auth_routes.py (or a new file)
# Note: You need 'from sqlalchemy.sql import text' imported above

# In auth_routes.py or dependencies.py

# The require_jwt function will need a small modification:
# async def require_jwt(Authorize: AuthJWT = Depends()):
#     # ... (JWT validation and blocklist check remain the same) ...
    
#     # The subject is the User ID (PK) as a string
#     user_id_str = Authorize.get_jwt_subject()
    
#     # Extract the tenant_id from the claims
#     claims = Authorize.get_raw_jwt()
#     tenant_id_str = claims.get("tenant_id") 
    
#     if not tenant_id_str:
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
#                             detail="Tenant information missing from token.")
    
#     try:
#         # Return both the user ID and the tenant ID (as integers)
#         return int(user_id_str), int(tenant_id_str)
#     except ValueError:
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
#                             detail="Invalid ID format in JWT.")


# --- THE NEW TENANT RLS DEPENDENCY ---
async def set_tenant_rls_context(
    auth_data: tuple[int, int] = Depends(require_jwt), # Returns (user_id, tenant_id)
    db: AsyncSession = Depends(get_async_db)
    ) -> int:
    """
    Sets the current authenticated user's Tenant ID in the PostgreSQL session variable.
    This enables Tenant-Level RLS and Partition Pruning.
    """
    
    # Unpack the tuple: (user_id, tenant_id)
    user_id, tenant_id = auth_data
    
    # 1. Set the RLS context using the TENANT ID
    try:
        # Set session variable for tenant
        await db.execute(
            text("SELECT set_config('session.current_tenant_id', :tenant_id::text, false)")
            .bindparams(tenant_id=tenant_id)
        )
        
        # OPTIONAL: You may also set the user_id for granular user-level policies
        # await db.execute(
        #     text("SELECT set_config('session.current_user_id', :user_id::text, false)")
        #     .bindparams(user_id=user_id)
        # )

    except Exception as e:
        print(f"ERROR: Tenant RLS Context Setup failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database context security setup failed."
        )
        
    # Return the tenant_id for the FastAPI route to optionally use
    return tenant_id

# HomePage Route
@auth_router.get("/")
async def hello():
    """
        ## A sample route to test JWT authentication.
        This route requires a valid JWT token to access.
        It returns a simple message "Hello World" if the token is valid.
        ### JWT Authentication Required
        - The JWT token must be included in the request header as `Authorization    Bearer <token>`.      
    """    
    return {"message": "Hello World from the Pizza Delivery API Auth Service"}

# SignUp Route
@auth_router.post("/register",response_model=None, 
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
        phone_number=user.phone_number,
        is_staff=user.is_staff,
        is_active=user.is_active
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    new_address = Address(
            user_id=new_user.id  # This populates the foreign key
        )
    db.add(new_address)
    await db.commit()
    
    return jsonable_encoder({"message": "User created successfully"})
    
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
    
    result = await db.execute(select(User.id, User.username, User.password, User.tenant_id,
                                     User.is_staff).where(User.username==user.username))
    
    db_user = result.first() # Tuple with (id, username, password, is_staff, tenant_id)
    
    if not db_user or not check_password_hash(db_user.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                            detail="Invalid username or password")
    
    # 2. Add tenant_id to the user_claims (private claims)
    access_token = Authorize.create_access_token(
        subject=str(db_user.id),
        expires_time=timedelta(minutes=15),
        user_claims={
            "is_staff": db_user.is_staff,
            "tenant_id": str(db_user.tenant_id) # Store as string for JWT
        }
    )
    refresh_token = Authorize.create_refresh_token(subject=str(db_user.id),
                                                   expires_time=timedelta(days=7))
    response = {
        "access": access_token,
        "refresh": refresh_token,
        "token_type": "bearer",
        "user_id": db_user.id,
        "tenant_id": db_user.tenant_id # Optional: return the ID to the client
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