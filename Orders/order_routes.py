# orders.py

# from fastapi import APIRouter, status, Depends, HTTPException
# from fastapi_jwt_auth import AuthJWT
# from Schemas.schemas_old import OrderResponseModel, OrderStatusUpdateModel, OrderListResponseModel, OrderCreateModel
# from Models.models import User, Order, OrderItem, ProductVariant, Product, Inventory, Address, Payment
# # ORDER_STATUSES
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.future import select
# from sqlalchemy.orm import selectinload
# from uuid import UUID
# from database_connection.database import get_async_db
# from datetime import datetime
# from decimal import Decimal
# import asyncio
# from typing import List, Dict, Any
# import uuid
from pydantic import BaseModel, Field, UUID4
from decimal import Decimal
import uuid
from fastapi import APIRouter, status, Depends, HTTPException
from fastapi_jwt_auth2 import AuthJWT
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
import asyncio
from Models.models import User, Order, OrderItem, ProductVariant, Product, Inventory, Address, Payment
from Schemas.schemas_old import (OrderCreateModel, OrderResponseModel, 
                                #  OrderStatusUpdateModel, 
                                OrderListResponseModel, 
                                 OrderItemResponseModel)
from database_connection.database import get_async_db
import logging

# Set up logging to track internal errors
logger = logging.getLogger(__name__)

order_router = APIRouter()

# --- Placeholder for Message Queue/Event Publishing ---
# In a real microservice architecture, this would publish a message 
# to Kafka, RabbitMQ, or a similar message broker.
async def publish_order_created_event(order_id: uuid.UUID):
    """
    Simulates publishing a message to a queue for asynchronous processing.
    """
    # NOTE: This would typically be a non-blocking network call to the message broker.
    # e.g., await kafka_producer.send('order_created', {'order_id': str(order_id)})
    print(f"--- EVENT: Order {order_id} created. Message queued for payment and inventory finalization. ---")
    await asyncio.sleep(0.001) # Very slight non-blocking pause simulation
    pass

# --------------------------------------------------------
# New dependency to get the current user object
async def get_current_user(Authorize: AuthJWT = Depends(), 
                           db: AsyncSession = Depends(get_async_db)):
    """
    Dependency to get the current authenticated user from the database.
    """
    Authorize.jwt_required()
    current_user_username = Authorize.get_jwt_subject()
    result = await db.execute(
        select(User).options(selectinload(User.addresses)).where(User.username == current_user_username)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

def get_staff_user(current_user: User = Depends(get_current_user)):
    """
    Dependency to ensure the current user is a staff member.
    """
    if not current_user.is_staff:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, 
                            detail="You are not authorized to perform this action")
    return current_user

@order_router.post("/create_order", response_model=OrderResponseModel, status_code=status.HTTP_201_CREATED)
async def place_order(
    order_data: OrderCreateModel,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    total_amount = Decimal("0.00")
    order_items_to_add = []
    transaction_reference = f"PIZZA-{uuid.uuid4().hex[:10].upper()}"

    # 1. Validate delivery address belongs to user
    address_stmt = select(Address).where(
        Address.id == order_data.delivery_address_id,
        Address.user_id == current_user.id
    )
    address_result = await db.execute(address_stmt)
    delivery_address = address_result.scalar_one_or_none()

    if not delivery_address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery address not found or unauthorized"
        )

    try:
        async with db.begin():
            for item_data in order_data.items:

                # A. Lock inventory row
                inventory_stmt = (
                    select(Inventory)
                    .where(Inventory.product_id == item_data.product_id)
                    .with_for_update()
                )
                inventory_res = await db.execute(inventory_stmt)
                inventory = inventory_res.scalar_one_or_none()

                if not inventory or inventory.quantity < item_data.quantity:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Insufficient stock for product {item_data.product_id}"
                    )

                # B. Fetch product
                product_res = await db.execute(
                    select(Product).where(Product.id == item_data.product_id)
                )
                product = product_res.scalar_one_or_none()

                if not product:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Product {item_data.product_id} not found"
                    )

                # C. Fetch variant (optional) - and ensure it belongs to the product
                variant = None
                price_modifier = Decimal("0.00")

                if item_data.variant_id:
                    variant_res = await db.execute(
                        select(ProductVariant).where(
                            ProductVariant.id == item_data.variant_id,
                            ProductVariant.product_id == product.id
                        )
                    )
                    variant = variant_res.scalar_one_or_none()

                    if not variant:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Variant {item_data.variant_id} not found for product {product.id}"
                        )

                    price_modifier = Decimal(str(variant.price_modifier))

                unit_price = Decimal(str(product.base_price)) + price_modifier
                total_amount += unit_price * item_data.quantity

                # D. Deduct stock
                inventory.quantity -= item_data.quantity

                # E. Create order item
                order_item = OrderItem(
                    product_id=product.id,
                    variant_id=item_data.variant_id,
                    quantity=item_data.quantity,
                    unit_price=unit_price
                )
                order_items_to_add.append(order_item)

            # 2. Create order
            new_order = Order(
                user_id=current_user.id,
                total_amount=total_amount,
                delivery_address_id=delivery_address.id,
                status="PENDING",
                items=order_items_to_add
            )
            db.add(new_order)
            await db.flush()

            # 3. Create payment
            new_payment = Payment(
                order_id=new_order.id,
                amount=total_amount,
                status="PENDING",
                method="DEBIT_CARD",
                transaction_id=transaction_reference
            )
            db.add(new_payment)

        # Reload full order for response
        result = await db.execute(
            select(Order)
            .options(
                selectinload(Order.items)
                .selectinload(OrderItem.product),
                selectinload(Order.items)
                .selectinload(OrderItem.variant)
            )
            .where(Order.id == new_order.id)
        )
        final_order = result.scalar_one()

        return OrderResponseModel(
            total_amount=final_order.total_amount,
            order_status=final_order.status,
            delivery_address_id=final_order.delivery_address_id,
            created_at=final_order.created_at,
            updated_at=final_order.updated_at,
            payment_reference=transaction_reference,
            items=[
                OrderItemResponseModel(
                    product_name=item.product.name,
                    variant_name=item.variant.name if item.variant else None,
                    quantity=item.quantity,
                    unit_price=item.unit_price
                )
                for item in final_order.items
            ]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Order Creation Failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while processing your order."
        )

# List All Orders (SuperAdmin Only)
# @order_router.get("/show_all_orders", response_model=OrderListResponseModel)
# async def list_all_orders(
#     db: AsyncSession = Depends(get_async_db),
#     staff_user: User = Depends(get_staff_user) # Use the staff dependency
# ):
#     """
#     List all orders. This route is restricted to staff members. (CQRS Target)
#     """
#     # NOTE: In a high-scale app, this would query the Read Model (e.g., Elasticsearch).
#     result = await db.execute(
#         select(Order).options(selectinload(Order.items).selectinload(OrderItem.product))
#     )
#     orders = result.scalars().all()
    
#     orders_response = []
#     for order in orders:
#         items_details = [
#             {"product_name": item.product.name, "quantity": item.quantity}
#             for item in order.items
#         ]
#         orders_response.append(create_order_response(order, items_details))

#     return {"message": "All orders retrieved successfully", "orders": orders_response}


# Get a specific order by ID (SuperAdmin Only)
@order_router.get("/get_order_admin/{order_id}", response_model=OrderResponseModel)
async def get_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    staff_user: User = Depends(get_staff_user) # Use the staff dependency
):
    """
    Get a specific order by ID. This route is restricted to staff members. (CQRS Target)
    """
    # NOTE: In a high-scale app, this would query the Read Model.
    result = await db.execute(
        select(Order).options(selectinload(Order.items).selectinload(OrderItem.product)).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        
    items_details = [
        {"product_name": item.product.name, "quantity": item.quantity}
        for item in order.items
    ]
    return create_order_response(order, items_details)


# Get Current User's Orders
@order_router.get("/get_orders", response_model=OrderListResponseModel)
async def get_my_orders(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve all orders for the current authenticated user. (CQRS Target)
    """
    # NOTE: In a high-scale app, this would query the Read Model.
    result = await db.execute(
        select(Order).options(selectinload(Order.items).selectinload(OrderItem.product)).where(Order.user_id == current_user.id)
    )
    orders = result.scalars().all()
    
    response = OrderListResponseModel(
        message="Current user's orders retrieved successfully",
        orders= [OrderResponseModel(
            total_amount=order.total_amount,
            order_status=order.status,
            delivery_address_id=order.delivery_address_id,
            created_at=order.created_at,
            updated_at=order.updated_at,
            payment_reference=order.payment.transaction_id if order.payment else None,
            items=[
                OrderItemResponseModel(
                    product_name=item.product.name,
                    variant_name=item.variant.name if item.variant else None,
                    quantity=item.quantity,
                    unit_price=item.unit_price
                )
                for item in order.items
            ]
        ) for order in orders]
    )

    return jsonable_encoder(response)


# Get Current User's Order by ID
@order_router.get("/get_order/{order_id}", response_model=OrderResponseModel)
async def get_my_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
    ):
    """
    Retrieve a specific order for the current authenticated user. (CQRS Target)
    """
    # NOTE: In a high-scale app, this would query the Read Model.
    result = await db.execute(
        select(Order).options(selectinload(Order.items).selectinload(OrderItem.product)).where(Order.id == order_id, Order.user_id == current_user.id)
    )
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found or does not belong to you")
    
    response = OrderResponseModel(
        total_amount=order.total_amount,
        order_status=order.status,
        delivery_address_id=order.delivery_address_id,
        created_at=order.created_at,
        updated_at=order.updated_at,
        payment_reference=order.payment.transaction_id if order.payment else None,
        items=[
            OrderItemResponseModel(
                product_name=item.product.name,
                variant_name=item.variant.name if item.variant else None,
                quantity=item.quantity,
                unit_price=item.unit_price
            )
            for item in order.items
        ]
    )

    return jsonable_encoder(response)


# # Update Order Status (SuperAdmin Only)
# @order_router.put("/update_order_status/{order_id}/", response_model=OrderStatusUpdateModel)
# async def update_order_status(
#     order_id: uuid.UUID,
#     updated_status: OrderStatusUpdateModel,
#     db: AsyncSession = Depends(get_async_db),
#     staff_user: User = Depends(get_staff_user) # Use the staff dependency
# ):
#     """
#     Update the status of an order. This route is restricted to staff members.
#     """
#     result = await db.execute(select(Order).where(Order.id == order_id))
#     order_to_update = result.scalar_one_or_none()
    
#     if not order_to_update:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        
#     # Find the corresponding enum value from the string
#     new_status_enum = None
#     # NOTE: This status mapping logic is assumed to be correct based on the original code
#     for status_option in Order.ORDER_STATUSES: 
#         if status_option[1].lower() == updated_status.order_status.lower():
#             new_status_enum = status_option[0]
#             break
            
#     if new_status_enum is None:
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status value")
        
#     order_to_update.status = new_status_enum
#     order_to_update.updated_at = datetime.utcnow()
    
#     await db.commit()
#     await db.refresh(order_to_update)
    
#     return {
#         "message": "Order status updated successfully",
#         "order_id": order_to_update.id,
#         # Access the status code property
#         "order_status": order_to_update.status.code, 
#         "updated_at": order_to_update.updated_at.isoformat(),
#     }


# Delete Order Route (Current User Only)
@order_router.delete("/delete_order/{order_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete an order. Requires PENDING status for the current user.
    """
    result = await db.execute(select(Order).where(Order.id == order_id, Order.user_id == current_user.id))
    order_to_delete = result.scalar_one_or_none()
        
    if not order_to_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found or does not belong to you")
    
    # Check the status of the order before deleting (ensure it's still cancellable)
    if order_to_delete.status != 'PENDING':
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete an order that is not in PENDING status")
    
    await db.delete(order_to_delete)
    await db.commit()
    
    # NOTE: A compensating event should be published here to 'un-reserve' inventory if necessary.
    
    return # Returns a 204 No Content response