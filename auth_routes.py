from fastapi import APIRouter, status, Depends
from sqlalchemy import exists
from database import engine, SessionLocal #, Session
from schemas import SignUpModel,UserResponseModel,LoginModel
from models import Customer, Order
from sqlalchemy.orm import Session as Session_v2
from fastapi.exceptions import HTTPException
from werkzeug.security import generate_password_hash, check_password_hash
from fastapi_jwt_auth import AuthJWT
from fastapi.encoders import jsonable_encoder

auth_router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)

# session = Session(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
# HomePage Route
@auth_router.get("/")
async def hello(
    Authorize: AuthJWT = Depends()
    ):
    try:
        Authorize.jwt_required()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                            detail="Invalid or expired token")
    return {"message": "Hello World"}

# SignUp Route
@auth_router.post("/signup",response_model=UserResponseModel, 
                  status_code=status.HTTP_201_CREATED)
async def signup(user: SignUpModel,db: Session_v2 = Depends(get_db)):
    if db.query(exists().where(Customer.username == user.username)).scalar():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
    if db.query(exists().where(Customer.email == user.email)).scalar():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")
    
    new_user = Customer(
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
    db.commit()
    return UserResponseModel.from_orm(new_user)
    
# Login Route
@auth_router.post("/login")
async def login(user: LoginModel, db: Session_v2 = Depends(get_db), Authorize: AuthJWT = Depends()):
    db_user = db.query(Customer).with_entities(Customer.username, Customer.password).filter_by(username=user.username).first()
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

@auth_router.get("/refresh")
async def refresh(Authorize: AuthJWT = Depends()):
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