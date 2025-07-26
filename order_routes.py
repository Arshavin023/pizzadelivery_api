from fastapi import APIRouter, status, Depends
from fastapi_jwt_auth import AuthJWT
from models import User, Order
from schemas import OrderModel,OrderResponseModel,OrderStatusUpdateModel,OrderListResponseModel
from database_connection.database import get_async_db  # <-- updated import
from fastapi.exceptions import HTTPException
from fastapi.encoders import jsonable_encoder
from datetime import datetime
from uuid import UUID 
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from redis_blacklist import add_token_to_blocklist, is_token_blocklisted


order_router = APIRouter()

async def require_jwt(Authorize: AuthJWT = Depends()):
    try:
        Authorize.jwt_required()
        raw_token = Authorize.get_raw_jwt()['jti']
        if is_token_blocklisted(raw_token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                            detail="Invalid or expired token")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid JWT header"
            )
    return Authorize.get_jwt_subject()

@order_router.get("/")
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

# Place Order Route
@order_router.post("/order", response_model=OrderResponseModel, 
                   status_code=status.HTTP_201_CREATED)
async def place_order(order: OrderModel, 
                      db: AsyncSession = Depends(get_async_db),  # <- AsyncSession here
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
    current_user = await require_jwt(Authorize)
    result = await db.execute(select(User.id).where(User.username == current_user))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    new_order = Order(
        pizza_size=order.pizza_size,
        quantity=order.quantity,
        flavour=order.flavour,
        user_id=user
    )

    db.add(new_order)
    await db.commit()
    await db.refresh(new_order)

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

# List All Orders Route SuperAdmin
@order_router.get("/list_all_orders", response_model=OrderListResponseModel)
async def list_all_orders(db: AsyncSession = Depends(get_async_db),
                     Authorize: AuthJWT = Depends()):
    """
    ## List All Orders
    This route allows a SuperAdmin to retrieve all orders placed by users.
    ### JWT Authentication Required
    - The JWT token must be included in the request header as `Authorization Bearer <token>`.
    ### Response
    - Returns a list of all orders with their details.
    """
    current_user = await require_jwt(Authorize)
    user = await db.execute(select(User.is_staff).where(User.username == current_user))
    is_staff = user.scalar_one_or_none()
    if is_staff:
        # Fetch all orders from the database
        result = await db.execute(select(Order.id,Order.flavour,Order.pizza_size,
                                         Order.quantity,Order.order_status,
                                         Order.time_created,Order.total_cost))
        orders = result.fetchall()

        order_items = [
        OrderResponseModel(
            order_id=order.id,
            flavour=order.flavour.code,
            pizza_size=order.pizza_size.code,
            quantity=order.quantity,
            total_cost=order.total_cost,
            order_status=order.order_status.code,
            time_created=order.time_created.isoformat() if isinstance(order.time_created, datetime) else str(order.time_created),
        ) for order in orders
        ]

        response =  OrderListResponseModel(message="SuperAdmin All Orders retrieved successfully",
                                           orders=order_items)

        return jsonable_encoder(response)
    
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, 
                            detail="You are not authorized to view all orders")

# Get Any User's Order Route
@order_router.get("/orders/{order_id}", response_model=OrderResponseModel)
async def get_specific_order(order_id:UUID, db: AsyncSession = Depends(get_async_db),
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
    current_user = await require_jwt(Authorize)
    user = await db.execute(select(User.is_staff).where(User.username == current_user))
    is_staff = user.scalar_one_or_none()
    if is_staff:
        result = await db.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                            detail="Order not found")
        response = {
            "order_id": order.id,
            "pizza_size": order.pizza_size_code,
            "quantity": order.quantity,
            "flavour": order.flavour_code,
            "total_cost": order.total,
            "order_status": order.order_status_code,
            "time_created": order.time_created.isoformat(),
        }
        return jsonable_encoder(response) # Return Order 
    
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, 
                            detail="You are not authorized to view this order")


# Get Current User's Orders Route
@order_router.get("/user/orders", response_model=OrderListResponseModel)
async def get_my_orders(db: AsyncSession = Depends(get_async_db),
                        Authorize: AuthJWT = Depends()):
    """
    ## Get Current User's Orders
    This route allows a user to retrieve all their orders.
    ### JWT Authentication Required
    - The JWT token must be included in the request header as `Authorization Bearer <token>`.
    ### Response
    - Returns a list of all orders placed by the current user with their details.
    """
    current_user = await require_jwt(Authorize)
    user = await db.execute(select(User.id).where(User.username == current_user))
    user = user.scalar_one_or_none()
    result = await db.execute(
        select(Order.id, Order.flavour,Order.pizza_size,
               Order.quantity,Order.order_status,Order.total_cost,
               Order.time_created).where(Order.user_id == user))
    orders = result.fetchall()

    order_items = [
        OrderResponseModel(
            order_id=order.id,
            flavour=order.flavour.code,
            pizza_size=order.pizza_size.code,
            quantity=order.quantity,
            total_cost=order.total_cost,
            order_status=order.order_status.code,
            time_created=order.time_created.isoformat() if isinstance(order.time_created, datetime) else str(order.time_created),
        ) for order in orders
        ]

    response =  OrderListResponseModel(message="CurrentUser All Orders retrieved successfully",
                                           orders=order_items)
   
    return jsonable_encoder(response)

# Get Current User's Order by ID Route
@order_router.get("/user/orders/order/{order_id}", response_model=OrderResponseModel)
async def get_my_order(order_id: UUID, 
                       db: AsyncSession = Depends(get_async_db),
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
    current_user = await require_jwt(Authorize)
    user = await db.execute(select(User.id).where(User.username == current_user))
    user = user.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    result = await db.execute(select(Order.id,Order.flavour,Order.pizza_size,
                                         Order.quantity,Order.order_status,Order.total_cost,
                                         Order.time_created).where(Order.user_id == user,
                                                                   Order.id == order_id))
    order = result.first()

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found") 
    
    (order_id, flavour, pizza_size, quantity,order_status,total_cost,time_created) = order

    response = {
        "order_id": order_id,
        "flavour": flavour.code,
        "pizza_size": pizza_size.code,
        "quantity": quantity,
        "total_cost": total_cost,
        "order_status": order_status.code,
        "time_created": time_created.isoformat(),
    }
  
    return jsonable_encoder(response)

# Update User's Order Route
@order_router.put("/order/update/{order_id}/", response_model=OrderResponseModel)
async def update_order(order_id: UUID, order: OrderModel, 
                       db: AsyncSession = Depends(get_async_db),
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
    current_user = await require_jwt(Authorize)
    user = await db.execute(select(User.id).where(User.username == current_user))
    user = user.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    result = await db.execute(select(Order).where(Order.user_id == user,Order.id == order_id))
    order_to_update = result.scalar_one_or_none()
    
    if not order_to_update:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                            detail="Order not found")
    
    order_to_update.pizza_size = order.pizza_size
    order_to_update.quantity = order.quantity
    order_to_update.flavour = order.flavour
    order_to_update.time_created = datetime.now()
    await db.commit()
    await db.refresh(order_to_update)

    response = {
        "order_id": order_to_update.id,
        "pizza_size": order_to_update.pizza_size_code,
        "quantity": order_to_update.quantity,
        "flavour": order_to_update.flavour_code,
        "total_cost": order_to_update.total,
        "order_status": order_to_update.order_status_code,
        "time_created": order_to_update.time_created.isoformat(),
    }
    return jsonable_encoder(response)
    

# Update Order Status Route SuperAdmin
@order_router.put("/order/update/status/{order_id}/", 
                  response_model=OrderStatusUpdateModel)
async def update_order_status(order_id: UUID,
                                updated_status: OrderStatusUpdateModel,
                               db: AsyncSession = Depends(get_async_db),
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
    current_user = await require_jwt(Authorize)
    user = await db.execute(select(User.is_staff).where(User.username == current_user))
    is_staff = user.scalar_one_or_none()
    # Check if the user is a staff member
    if not is_staff:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, 
                            detail="You are not authorized to update order status")
    
    result = await db.execute(select(Order).where(Order.id == order_id))
    order_to_update = result.scalar_one_or_none()
    
    if not order_to_update:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                            detail="Order not found")
    
    order_to_update.order_status = updated_status.order_status
    order_to_update.time_created = datetime.now()
    await db.commit()
    await db.refresh(order_to_update)
    
    response = {
        "message": "Order status updated successfully",
        "order_id": order_to_update.id,
        "order_status": order_to_update.order_status_code,
        "time_created": order_to_update.time_created.isoformat(),
    }
    
    return jsonable_encoder(response)

# Delete Order Route
@order_router.delete("/order/delete/{order_id}/", 
                     status_code=status.HTTP_204_NO_CONTENT
                    #  response_model=OrderResponseModel
                     )
async def delete_order(order_id: UUID,
                       db: AsyncSession = Depends(get_async_db),
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
    current_user = await require_jwt(Authorize)
    user = await db.execute(select(User.id).where(User.username == current_user))
    user = user.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    result = await db.execute(select(Order).where(Order.user_id == user,Order.id == order_id))
    order_to_delete = result.scalar_one_or_none()
        
    if not order_to_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                            detail="Order not found")
    
    await db.delete(order_to_delete)
    await db.commit()
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
    # return "Order deleted successfully"  # Return success message without order details