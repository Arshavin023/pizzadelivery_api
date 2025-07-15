from fastapi import APIRouter, status, Depends
from fastapi_jwt_auth import AuthJWT
from models import User, Address
from schemas import (UserResponseModel, UserUpdateModel, UserListResponseModel, 
                     AddressResponseModel,AddressUpdateModel)
from database_connection.database import get_async_db  # <-- updated import
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.exceptions import HTTPException
from fastapi_jwt_auth.exceptions import (
    MissingTokenError,
    InvalidHeaderError,
    RevokedTokenError,
    AccessTokenRequired,
    JWTDecodeError
)
from fastapi.encoders import jsonable_encoder
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy import update, and_
from sqlalchemy.orm import selectinload
import re 

# Add this phone validation pattern
PHONE_REGEX = re.compile(r'^\+?[1-9]\d{1,14}$')  # E.164 format

user_router = APIRouter(prefix="/users", tags=["Users"])

async def require_jwt(Authorize: AuthJWT = Depends()):
    try:
        Authorize.jwt_required()
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

@user_router.get("/")
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

# Get User Info Route
@user_router.get("/profile", response_model=UserResponseModel, 
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

    # Eager-load addresses
    result = await db.execute(
        select(User)
        .options(selectinload(User.addresses))
        .where(User.username == current_user)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Determine default address (used for full_address)
    default_address = next((a for a in user.addresses if a.is_default), None)
    if not default_address and user.addresses:
        default_address = user.addresses[0]

    # Build all addresses for nested response
    address_models = []
    for addr in user.addresses:
        address_models.append(AddressResponseModel(
            address_type=addr.address_type.code if addr.address_type else None,
            street_address1=addr.street_address1,
            street_address2=addr.street_address2,
            postal_code=addr.postal_code,
            city=addr.city,
            state=addr.state,
            country=addr.country,
            full_address=addr.full_address,
            is_default=addr.is_default,
            updated_at=addr.updated_at
        ))

    response = UserResponseModel(
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        phone_number=user.phone_number,
        is_staff=user.is_staff,
        is_active=user.is_active,
        full_address=default_address.full_address if default_address else None,
        addresses=address_models
    )

    return jsonable_encoder(response)

# Get All Users Route SuperAdmin    
@user_router.get("/profiles/", response_model=UserListResponseModel, 
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
    # Get the requesting user's full record
    # Fetch only what is needed: is_staff flag
    result = await db.execute(
        select(User.is_staff).where(User.username == current_user)
    )
    user_row = result.first()

    if not user_row or not user_row.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource"
        )
    
    # Get all users (full ORM model)
    result = await db.execute(
    select(User).options(selectinload(User.addresses))
    )
    users = result.scalars().all()

    user_list = []

    for user in users:
        # Get default address or fallback
        default_address = next((a for a in user.addresses if a.is_default), None)
        if not default_address and user.addresses:
            default_address = user.addresses[0]

        # Build nested list of addresses
        address_models = [
            AddressResponseModel(
                address_type=a.address_type.code if a.address_type else None,
                street_address1=a.street_address1,
                street_address2=a.street_address2,
                postal_code=a.postal_code,
                city=a.city,
                state=a.state,
                country=a.country,
                full_address=a.full_address,
                is_default=a.is_default,
                updated_at=a.updated_at
            )
            for a in user.addresses
        ]

        user_list.append(
            UserResponseModel(
                id=user.id,
                username=user.username,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                phone_number=user.phone_number,
                is_staff=user.is_staff,
                is_active=user.is_active,
                full_address=default_address.full_address if default_address else None,
                addresses=address_models,
                updated_at=default_address.updated_at if default_address else None
            )
        )

    response = UserListResponseModel(
        message="All users retrieved successfully",
        users=user_list
    )

    return jsonable_encoder(response)


# Update User Info Route
@user_router.put("/update/user", response_model=UserResponseModel, 
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
    
    # Get user with addresses eager loaded
    current_user = await require_jwt(Authorize)

    async with db.begin():

        result = await db.execute(
            select(User)
            .options(selectinload(User.addresses))
            .where(User.username == current_user)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Update basic user fields
        update_data = user_update.dict(exclude_unset=True)
        for field in ['first_name', 'last_name', 'phone_number']:
            if field in update_data:
                setattr(user, field, update_data[field])

        # user.updated_at = datetime.now()  # Update timestamp
        
        await db.commit()
        
        # Refresh with relationships
        await db.refresh(user)
        result = await db.execute(
            select(User)
            .options(selectinload(User.addresses))
            .where(User.id == user.id)
        )
        updated_user = result.scalar_one()

    # Prepare response
    default_address = next((a for a in updated_user.addresses if a.is_default), None)
    if not default_address and updated_user.addresses:
        default_address = updated_user.addresses[0]

    address_models = [
        AddressResponseModel(
            id=addr.id,
            address_type=addr.address_type.code if addr.address_type else None,
            street_address1=addr.street_address1,
            street_address2=addr.street_address2,
            postal_code=addr.postal_code,
            city=addr.city,
            state=addr.state,
            country=addr.country,
            full_address=addr.full_address,
            is_default=addr.is_default,
            updated_at=addr.updated_at
        )
        for addr in updated_user.addresses
    ]

    response = UserResponseModel(
        id=updated_user.id,
        username=updated_user.username,
        email=updated_user.email,
        first_name=updated_user.first_name,
        last_name=updated_user.last_name,
        phone_number=updated_user.phone_number,
        is_staff=updated_user.is_staff,
        is_active=updated_user.is_active,
        full_address=default_address.full_address if default_address else None,
        addresses=address_models,
        created_at=updated_user.created_at,
        updated_at=updated_user.updated_at
    )
    return jsonable_encoder(response)

# Update User Address Info Route
@user_router.put("/update/address", response_model=AddressResponseModel, 
                     status_code=status.HTTP_200_OK)
async def update_user_address(address_update: AddressUpdateModel, Authorize: AuthJWT = Depends(), 
                           db: AsyncSession = Depends(get_async_db)):
    """
    ## User Address Information
    This route allows the currently authenticated user to update their address information.
    ### JWT Authentication Required
    - The JWT token must be included in the request header as `Authorization Bearer <token>`.
    ### Request Body
    - The request body should contain the fields to be updated, such as `first_name`, `last_name`, `address`, `state`, `local_government`, and `phone_number`.
    ### Response
    - Returns a message indicating successful update along with the updated user information.
    """
    
    # Get user with addresses eager loaded
    current_user = await require_jwt(Authorize)
    
    async with db.begin():
        # First get the user ID
        user_result = await db.execute(
            select(User).where(User.username == current_user)
        )
        user = user_result.scalar_one()
        
        # Try to find existing address of this type
        address_result = await db.execute(
            select(Address)
            .where(
                and_(
                    Address.user_id == user.id,
                    Address.address_type == address_update.address_type
                )
            )
        )
        address = address_result.scalar_one_or_none()
        
        if address:
            # Update address fields
            update_data = address_update.dict(exclude_unset=True, exclude={"address_type"})
            for field, value in update_data.items():
                setattr(address, field, value)
        # If it doesn't exist, create a new one
        else:
            address_data = address_update.dict(exclude_unset=True)
            address = Address(
                user_id=user.id,
                **address_data
            )
            db.add(address)

        # Handle default address setting
        if address_update.is_default:
            # Reset any existing default addresses
            await db.execute(
                update(Address)
                .where(
                    and_(
                        Address.user_id == user.id,
                        Address.is_default == True,
                        Address.id != address.id  # Don't reset the current address
                    )
                )
                .values(is_default=False)
            )
            address.is_default = True
    
    # Refresh and return the updated address
    await db.refresh(address)
    return AddressResponseModel.from_orm(address)


    