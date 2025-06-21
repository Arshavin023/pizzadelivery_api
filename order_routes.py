from fastapi import APIRouter, status, Depends
from fastapi_jwt_auth import AuthJWT
from models import User, Order
from schemas import OrderModel,OrderResponseModel,OrderStatusUpdateModel
from database import engine, SessionLocal #, Session
from sqlalchemy.orm import Session as Session_v2
from fastapi.exceptions import HTTPException
from fastapi.encoders import jsonable_encoder
from datetime import datetime
from uuid import UUID 
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

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

# Place Order Route
@order_router.post("/order", response_model=OrderResponseModel, 
                   status_code=status.HTTP_201_CREATED)
async def place_order(order: OrderModel, db: Session_v2 = Depends(get_db),
                       Authorize: AuthJWT = Depends()):
    """
        ## Place an Order
        This route allows a user to place an order for a pizza.
        ### JWT Authentication Required
        - The JWT token must be included in the request header as `Authorization Bearer <token>`.
        ### Request Body
        - `pizza_size`: The size of the pizza (e.g., SMALL, MEDIUM, LARGE).
        - `quantity`: The number of pizzas to order.
        - `flavour`: The flavour of the pizza (e.g., PEPPERONI, MARGHERITA).
        ### Response            
    """
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
    """
    ## List All Orders
    This route allows a SuperAdmin to retrieve all orders placed by users.
    ### JWT Authentication Required
    - The JWT token must be included in the request header as `Authorization Bearer <token>`.
    ### Response
    - Returns a list of all orders with their details.
    """
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
    """
    ## Get Specific Order
    This route allows a SuperAdmin to retrieve a specific order by its ID.
    ### JWT Authentication Required
    - The JWT token must be included in the request header as `Authorization Bearer <token>`.
    ### Parameters
    - `order_id`: The ID of the order to retrieve.
    ### Response
    - Returns the details of the specified order.   
    """
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
    """
    ## Get Current User's Orders
    This route allows a user to retrieve all their orders.
    ### JWT Authentication Required
    - The JWT token must be included in the request header as `Authorization Bearer <token>`.
    ### Response
    - Returns a list of all orders placed by the current user with their details.
    """
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
    """
    ## Get Current User's Order by ID
    This route allows a user to retrieve a specific order by its ID.
    ### JWT Authentication Required
    - The JWT token must be included in the request header as `Authorization Bearer <token>`.
    ### Parameters
    - `order_id`: The ID of the order to retrieve.
    ### Response
    - Returns the details of the specified order placed by the current user.
    """
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

# Update User's Order Route
@order_router.put("/order/update/{order_id}/", response_model=OrderResponseModel)
async def update_order(order_id: UUID, order: OrderModel, db: Session_v2 = Depends(get_db),
                          Authorize: AuthJWT = Depends()):
    """
    ## Update User's Order
    # This route allows a user to update their existing order.
    ### JWT Authentication Required
    - The JWT token must be included in the request header as `Authorization Bearer <token>`.
    ### Parameters
    - `order_id`: The ID of the order to update.
    ### Request Body
    - `pizza_size`: The new size of the pizza (e.g., SMALL, MEDIUM, LARGE).
    - `quantity`: The new number of pizzas to order.
    - `flavour`: The new flavour of the pizza (e.g., PEPPERONI, MARGHERITA).
    ### Response
    - Returns the updated order details.
    """
    try:
        Authorize.jwt_required()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                            detail="Invalid or expired token")
    
    current_user = Authorize.get_jwt_subject()
    user = db.query(User).with_entities(User.id).filter(User.username == current_user).first()
    
    existing_order = db.query(Order).filter(Order.id == order_id, Order.user_id == user.id).first()
    
    if not existing_order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                            detail="Order not found")
    
    existing_order.pizza_size = order.pizza_size
    existing_order.quantity = order.quantity
    existing_order.flavour = order.flavour
    existing_order.time_created = datetime.now()
    db.commit()
    response = {
        "message": "Order updated successfully",
        "order_id": existing_order.id,
        "pizza_size": existing_order.pizza_size_code,
        "quantity": existing_order.quantity,
        "flavour": existing_order.flavour_code,
        "total_cost": existing_order.total,
        "order_status": existing_order.order_status_code,
        "time_created": existing_order.time_created.isoformat(),
    }
    return jsonable_encoder(response)

# Update Order Status Route SuperAdmin
@order_router.put("/order/update/status/{order_id}/", 
                  response_model=OrderResponseModel)
async def update_order_status(order_id: UUID,
                                order_status: OrderStatusUpdateModel,
                               db: Session_v2 = Depends(get_db),
                              Authorize: AuthJWT = Depends()):
    """
    ## Update Order Status
    This route allows a SuperAdmin to update the status of an order.
    ### JWT Authentication Required
    - The JWT token must be included in the request header as `Authorization Bearer <token>`.
    ### Parameters
    - `order_id`: The ID of the order to update.
    ### Request Body
    - `order_status`: The new status of the order (e.g., PENDING, DELIVERED).
    ### Response
    - Returns the updated order details.
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
                            detail="You are not authorized to update order status")
    
    order_to_update = db.query(Order).filter(Order.id == order_id).first()
    
    if not order_to_update:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                            detail="Order not found")
    
    order_to_update.order_status = order_status.order_status
    order_to_update.time_created = datetime.now()
    db.commit()
    
    response = {
        "message": "Order status updated successfully",
        "order_id": order_to_update.id,
        "pizza_size": order_to_update.pizza_size_code,
        "quantity": order_to_update.quantity,
        "flavour": order_to_update.flavour_code,
        "total_cost": order_to_update.total,
        "order_status": order_to_update.order_status_code,
        "time_created": order_to_update.time_created.isoformat(),
    }
    
    return jsonable_encoder(response)

# Delete Order Route
@order_router.delete("/order/delete/{order_id}/", 
                     status_code=status.HTTP_204_NO_CONTENT,
                     response_model=None)
async def delete_order(order_id: UUID, db: Session_v2 = Depends(get_db),
                       Authorize: AuthJWT = Depends()):
    """
    ## Delete Order
    This route allows a user to delete their order by its ID.
    ### JWT Authentication Required
    - The JWT token must be included in the request header as `Authorization Bearer <token>`.
    ### Parameters
    - `order_id`: The ID of the order to delete.
    ### Response
    - Returns a success message if the order is deleted successfully.
    """
    try:
        Authorize.jwt_required()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                            detail="Invalid or expired token")
    
    current_user = Authorize.get_jwt_subject()
    user = db.query(User).with_entities(User.id).filter(User.username == current_user).first()
    
    order_to_delete = db.query(Order).filter(Order.id == order_id, Order.user_id == user.id).first()
    
    if not order_to_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                            detail="Order not found")
    
    db.delete(order_to_delete)
    db.commit()
    response = {
        "message": "Order deleted successfully",
        "order_id": order_to_delete.id,
        "pizza_size": order_to_delete.pizza_size_code,
        "quantity": order_to_delete.quantity,
        "flavour": order_to_delete.flavour_code,
        "total_cost": order_to_delete.total,
        "order_status": order_to_delete.order_status_code,
        "time_created": order_to_delete.time_created.isoformat(),
    }
    return jsonable_encoder(response)

# @order_router.delete("/order/delete/{order_id}/", 
#                      status_code=status.HTTP_204_NO_CONTENT,
#                      response_model=None)
# async def delete_order(order_id: UUID, 
#                        db: AsyncSession = Depends(get_db),
#                        Authorize: AuthJWT = Depends()):
#     try:
#         await Authorize.jwt_required()  # Make sure this is awaitable
#     except Exception:
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
#                             detail="Invalid or expired token")

#     current_user = Authorize.get_jwt_subject()

#     # Fetch user ID asynchronously
#     result = await db.execute(
#         select(User.id).where(User.username == current_user)
#     )
#     user = result.scalar_one_or_none()

#     if not user:
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
#                             detail="User not found")

#     # Fetch the order asynchronously
#     result = await db.execute(
#         select(Order).where(Order.id == order_id, Order.user_id == user)
#     )
#     order_to_delete = result.scalar_one_or_none()

#     if not order_to_delete:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
#                             detail="Order not found")

#     # Delete the order
#     await db.delete(order_to_delete)
#     await db.commit()

#     response = {
#         "message": "Order deleted successfully",
#         "order_id": order_to_delete.id,
#         "pizza_size": order_to_delete.pizza_size_code,
#         "quantity": order_to_delete.quantity,
#         "flavour": order_to_delete.flavour_code,
#         "total_cost": order_to_delete.total,
#         "order_status": order_to_delete.order_status_code,
#         "time_created": order_to_delete.time_created.isoformat(),
#     }

#     return jsonable_encoder(response)