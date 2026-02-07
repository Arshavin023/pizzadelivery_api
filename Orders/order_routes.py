# orders.py

from fastapi import APIRouter, status, Depends, HTTPException
from fastapi_jwt_auth import AuthJWT
from Schemas.schemas import OrderResponseModel, OrderStatusUpdateModel, OrderListResponseModel, OrderCreateModel
from Models.models import User, Order, OrderItem, ProductVariant, Product, Inventory, Address, Payment
# ORDER_STATUSES
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from uuid import UUID
from database_connection.database import get_async_db
from datetime import datetime
from decimal import Decimal
import asyncio
from typing import List, Dict, Any


order_router = APIRouter()

# --- Placeholder for Message Queue/Event Publishing ---
# In a real microservice architecture, this would publish a message 
# to Kafka, RabbitMQ, or a similar message broker.
async def publish_order_created_event(order_id: UUID):
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

# New dependency for staff authorization
def get_staff_user(current_user: User = Depends(get_current_user)):
    """
    Dependency to ensure the current user is a staff member.
    """
    if not current_user.is_staff:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, 
                            detail="You are not authorized to perform this action")
    return current_user

# Helper function to create an OrderResponseModel from an Order object
def create_order_response(order: Order, items_details: List[Dict[str, Any]]):
    return {
        "order_id": order.id,
        "total_amount": order.total_amount,
        "order_status": order.status.code if hasattr(order.status, 'code') else order.status,
        "delivery_address_id": order.delivery_address_id,
        "created_at": order.created_at.isoformat(),
        "updated_at": order.updated_at.isoformat(),
        "items": items_details
    }

# --- SCALABLE PLACE ORDER ROUTE ---
@order_router.post("/create_order", response_model=OrderResponseModel, 
                   status_code=status.HTTP_201_CREATED)
async def place_order(
    order_data: OrderCreateModel,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
    ):
    """
    Place an order. This route implements atomic inventory reservation 
    using database locking and immediately returns, offloading payment and 
    final updates to an asynchronous message queue.
    """
    # 1. Validate delivery address
    # This remains outside the critical transaction as it is a read-only check.
    address_result = await db.execute(
        select(Address).where(Address.id == order_data.delivery_address_id, Address.user_id == current_user.id)
    )
    delivery_address = address_result.scalar_one_or_none()
    if not delivery_address:
        raise HTTPException(status_code=404, 
                            detail="Delivery address not found or does not belong to the current user")

    total_amount = Decimal(0.00)
    order_items_to_add = []
    items_details_response = []
    
    # --- START CRITICAL TRANSACTION: Order Creation and Atomic Inventory Lock ---
    # We use a transaction block to ensure atomicity. If any step fails, everything rolls back.
    async with db.begin():
        # 2. Process order items, calculate cost, and RESERVATION/DEDUCTION
        for item_data in order_data.items:
            # Fetch product and variant details (non-locking reads)
            product_result = await db.execute(select(Product).where(Product.id == item_data.product_id))
            product = product_result.scalar_one_or_none()
            if not product:
                raise HTTPException(status_code=404, detail=f"Product with ID {item_data.product_id} not found")

            variant = None
            if item_data.variant_id:
                variant_result = await db.execute(select(ProductVariant).where(ProductVariant.id == item_data.variant_id))
                variant = variant_result.scalar_one_or_none()
                if not variant or variant.product_id != product.id:
                    raise HTTPException(status_code=404, 
                                        detail=f"Variant with ID {item_data.variant_id} not found for this product")

            # Calculate item price
            item_price = product.base_price + (variant.price_modifier if variant else Decimal(0.00))
            total_amount += item_price * item_data.quantity
            
            # **ATOMIC INVENTORY CHECK AND DEDUCTION (Pessimistic Locking)**
            # Use 'select(Inventory).with_for_update()' to lock the row(s) to prevent overselling
            inventory_stmt = select(Inventory).where(Inventory.product_id == item_data.product_id).with_for_update(nowait=True)
            inventory_result = await db.execute(inventory_stmt)
            inventory = inventory_result.scalar_one_or_none()

            if not inventory or inventory.quantity < item_data.quantity:
                # This will automatically trigger a rollback of the transaction block
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, 
                    detail=f"Insufficient stock for product ID {item_data.product_id}. Available: {inventory.quantity if inventory else 0}"
                )

            # Deduct (Reserve) the quantity. This deduction is now atomic with the order creation.
            inventory.quantity -= item_data.quantity
            
            # Create the OrderItem model instance
            order_item = OrderItem(
                product_id=product.id,
                variant_id=variant.id if variant else None,
                quantity=item_data.quantity,
                unit_price=item_price
            )
            order_items_to_add.append(order_item)
            items_details_response.append({
                "product_name": product.name,
                "variant_name": variant.name if variant else None,
                "quantity": item_data.quantity,
                "unit_price": item_price
            })

        # 3. Create the new order
        # This occurs within the locked transaction, guaranteeing consistency.
        new_order = Order(
            user_id=current_user.id,
            total_amount=total_amount,
            delivery_address_id=delivery_address.id,
            items=order_items_to_add,
            # NOTE: Set initial status to PENDING or RESERVED
            status='PENDING' 
        )
        
        db.add(new_order)
        
        # db.commit() is implicit upon successful exit of the `async with db.begin()` block
    
    # db.refresh() must occur outside the transaction block if it was implicit
    await db.refresh(new_order) 
    
    # 4. Publish Event to Message Queue (Kafka/RabbitMQ)
    # This triggers decoupled processing for payment, notifications, and final order status updates.
    await publish_order_created_event(new_order.id)

    return create_order_response(new_order, items_details_response)
# --------------------------------------------------

# --- NOTE ON READ ROUTES FOR SCALE ---
# For 1 Billion users, these read routes (show_all_orders, get_my_orders, etc.) 
# should ideally be hitting a separate, read-optimized data store (e.g., Elasticsearch or a Read Replica),
# instead of performing heavy ORM queries with selectinload on the transactional database.
# The code below is kept for completeness but is a primary target for CQRS.
# -------------------------------------

# List All Orders (SuperAdmin Only)
@order_router.get("/show_all_orders", response_model=OrderListResponseModel)
async def list_all_orders(
    db: AsyncSession = Depends(get_async_db),
    staff_user: User = Depends(get_staff_user) # Use the staff dependency
):
    """
    List all orders. This route is restricted to staff members. (CQRS Target)
    """
    # NOTE: In a high-scale app, this would query the Read Model (e.g., Elasticsearch).
    result = await db.execute(
        select(Order).options(selectinload(Order.items).selectinload(OrderItem.product))
    )
    orders = result.scalars().all()
    
    orders_response = []
    for order in orders:
        items_details = [
            {"product_name": item.product.name, "quantity": item.quantity}
            for item in order.items
        ]
        orders_response.append(create_order_response(order, items_details))

    return {"message": "All orders retrieved successfully", "orders": orders_response}


# Get a specific order by ID (SuperAdmin Only)
@order_router.get("/show_any_order/{order_id}", response_model=OrderResponseModel)
async def get_specific_order(
    order_id: UUID,
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
@order_router.get("/show_orders", response_model=OrderListResponseModel)
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
    
    orders_response = []
    for order in orders:
        items_details = [
            {"product_name": item.product.name, "quantity": item.quantity}
            for item in order.items
        ]
        orders_response.append(create_order_response(order, items_details))

    return {"message": "Current user's orders retrieved successfully", "orders": orders_response}


# Get Current User's Order by ID
@order_router.get("/show_order/{order_id}", response_model=OrderResponseModel)
async def get_my_order(
    order_id: UUID,
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
        
    items_details = [
        {"product_name": item.product.name, "quantity": item.quantity}
        for item in order.items
    ]
    return create_order_response(order, items_details)


# Update Order Status (SuperAdmin Only)
@order_router.put("/update_order_status/{order_id}/", response_model=OrderStatusUpdateModel)
async def update_order_status(
    order_id: UUID,
    updated_status: OrderStatusUpdateModel,
    db: AsyncSession = Depends(get_async_db),
    staff_user: User = Depends(get_staff_user) # Use the staff dependency
):
    """
    Update the status of an order. This route is restricted to staff members.
    """
    result = await db.execute(select(Order).where(Order.id == order_id))
    order_to_update = result.scalar_one_or_none()
    
    if not order_to_update:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        
    # Find the corresponding enum value from the string
    new_status_enum = None
    # NOTE: This status mapping logic is assumed to be correct based on the original code
    for status_option in Order.ORDER_STATUSES: 
        if status_option[1].lower() == updated_status.order_status.lower():
            new_status_enum = status_option[0]
            break
            
    if new_status_enum is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status value")
        
    order_to_update.status = new_status_enum
    order_to_update.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(order_to_update)
    
    return {
        "message": "Order status updated successfully",
        "order_id": order_to_update.id,
        # Access the status code property
        "order_status": order_to_update.status.code, 
        "updated_at": order_to_update.updated_at.isoformat(),
    }


# Delete Order Route (Current User Only)
@order_router.delete("/delete_order/{order_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(
    order_id: UUID,
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