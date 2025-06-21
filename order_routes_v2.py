# orders_routes.py

from fastapi import APIRouter, status, Depends
from fastapi_jwt_auth import AuthJWT
from models import User, Order
from schemas import OrderModel, OrderResponseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi.exceptions import HTTPException
from fastapi.encoders import jsonable_encoder
from database_v2 import get_async_db  # <-- updated import

order_router = APIRouter(
    prefix="/orders",
    tags=["orders"]
)

@order_router.post("/order", response_model=OrderResponseModel, 
                   status_code=status.HTTP_201_CREATED)
async def place_order(
    order: OrderModel,
    db: AsyncSession = Depends(get_async_db),  # <- AsyncSession here
    Authorize: AuthJWT = Depends()
):
    try:
        Authorize.jwt_required()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid or expired token"
        )

    current_user = Authorize.get_jwt_subject()

    # Async query for user
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

    return jsonable_encoder(response)
