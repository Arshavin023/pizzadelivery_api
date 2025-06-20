from fastapi import APIRouter, status, Depends
from fastapi_jwt_auth import AuthJWT
from models import User, Order
from schemas import OrderModel,OrderResponseModel
from database import engine, SessionLocal #, Session
from sqlalchemy.orm import Session as Session_v2
from fastapi.exceptions import HTTPException
from fastapi.encoders import jsonable_encoder
from datetime import datetime
from uuid import UUID 

order_router = APIRouter(
    prefix="/orders",
    tags=["orders"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@order_router.get("/")
async def hello(Authorize: AuthJWT = Depends()):
    try:
        Authorize.jwt_required()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                             detail="Invalid JWT header")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                            detail="Invalid or expired token")
    return {"message": "Hello World"}

# Place Order Route
@order_router.post("/order", response_model=OrderResponseModel, 
                   status_code=status.HTTP_201_CREATED)
async def place_order(order: OrderModel, db: Session_v2 = Depends(get_db),
                       Authorize: AuthJWT = Depends()):
    try:
        Authorize.jwt_required()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                            detail="Invalid or expired token")
    
    current_user = Authorize.get_jwt_subject()
    user = db.query(User).with_entities(User.id).filter(User.username == current_user).first()
    new_order = Order(
        pizza_size=order.pizza_size,
        quantity=order.quantity,
        flavour=order.flavour
    )
    new_order.user_id = user.id

    db.add(new_order)
    db.commit()

    response = {
        "message": "Order placed successfully",
        "order_id": new_order.id,
        "pizza_size": new_order.pizza_size_code,
        "quantity": new_order.quantity,
        "flavour": new_order.flavour_code,
        "total_cost": new_order.total,
        "order_status": new_order.order_status_code,
        "time_created": new_order.time_created.isoformat(),
    }
    # return 'successfully created order'
    return jsonable_encoder(response)  # Return the newly created order as a JSON respons

# List All Orders Route
@order_router.get("/list_all_orders", response_model=None)
async def list_all_orders(db: Session_v2 = Depends(get_db),
                     Authorize: AuthJWT = Depends()):
    try:
        Authorize.jwt_required()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                            detail="Invalid or expired token")
    
    current_user = Authorize.get_jwt_subject()
    user = db.query(User).with_entities(User.is_staff).filter(User.username == current_user).first()
    if user.is_staff:
        orders = db.query(Order).with_entities(Order.id,Order.flavour,
                                               Order.quantity,Order.order_status,
                                               Order.time_created).all()
        response = {"message": "SuperAdmin All Orders retrieved successfully",
        "orders": [
        {
            "order_id": order.id,
            "flavour": order.flavour.code,
            "quantity": order.quantity,
            "order_status": order.order_status.code,
            "time_created": order.time_created.isoformat() if isinstance(order.time_created, datetime) else order.time_created,
        }
        for order in orders]}


        return jsonable_encoder(response)
    
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, 
                            detail="You are not authorized to view all orders")

# Get Any User's Order Route
@order_router.get("/orders/{order_id}", response_model=OrderResponseModel)
async def get_specific_order(order_id:UUID, db: Session_v2 = Depends(get_db),
                          Authorize: AuthJWT = Depends()):
    try:
        Authorize.jwt_required()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                            detail="Invalid or expired token")
    current_user = Authorize.get_jwt_subject()
    user = db.query(User).with_entities(User.is_staff).filter(User.username == current_user).first()
    if user.is_staff:
        order = db.query(Order).filter(Order.id == order_id).first()  
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                            detail="Order not found")
        response = {
            "message": "SuperAdmin SpecificOrder retrieved successfully",
            "order_id": order.id,
            "pizza_size": order.pizza_size_code,
            "quantity": order.quantity,
            "flavour": order.flavour_code,
            "total_cost": order.total,
            "order_status": order.order_status_code,
            "time_created": order.time_created.isoformat(),
        }
        # return 'successfully created order'
        return jsonable_encoder(response) # Return Order 
    
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, 
                            detail="You are not authorized to view this order")


# Get Current User's Orders Route
@order_router.get("/user/orders", response_model=None)
async def get_my_orders(db: Session_v2 = Depends(get_db),
                        Authorize: AuthJWT = Depends()):
    try:
        Authorize.jwt_required()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                            detail="Invalid or expired token")
    
    current_user = Authorize.get_jwt_subject()
    user = db.query(User).with_entities(User.id).filter(User.username == current_user).first()
    
    orders = db.query(Order).filter(Order.user_id == user.id).all()

    response = {"message": "CurrentUser All Orders retrieved successfully",
        "orders": [
        {
            "order_id": order.id,
            "flavour": order.flavour.code,
            "pizza_size": order.pizza_size.code,
            "quantity": order.quantity,
            "total_cost": order.total,
            "order_status": order.order_status.code,
            "time_created": order.time_created.isoformat() if isinstance(order.time_created, datetime) else order.time_created,
        }
        for order in orders]}
   
    return jsonable_encoder(response)

# Get Current User's Order by ID Route
@order_router.get("/user/orders/order/{order_id}", response_model=OrderResponseModel)
async def get_my_order(order_id: UUID, db: Session_v2 = Depends(get_db),
                       Authorize: AuthJWT = Depends()):
    try:
        Authorize.jwt_required()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                            detail="Invalid or expired token")
    
    current_user = Authorize.get_jwt_subject()
    user = db.query(User).with_entities(User.id).filter(User.username == current_user).first()
    
    order = db.query(Order).filter(Order.id == order_id, Order.user_id == user.id).first()
    
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                            detail="Order not found")
    
    response = {
        "message": "CurrentUser SpecificOrder retrieved successfully",
        "order_id": order.id,
        "pizza_size": order.pizza_size_code,
        "quantity": order.quantity,
        "flavour": order.flavour_code,
        "total_cost": order.total,
        "order_status": order.order_status_code,
        "time_created": order.time_created.isoformat(),
    }
    
    return jsonable_encoder(response)