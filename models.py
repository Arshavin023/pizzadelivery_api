from database_connection.database import Base
import uuid
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import (Column, JSON, ForeignKey,BigInteger, 
                        Integer, Boolean, Text, String, DateTime, Numeric)
from sqlalchemy_utils.types import ChoiceType
from datetime import datetime
from sqlalchemy.orm import relationship, validates
from sqlalchemy import event  
from sqlalchemy import func, JSON

class User(Base):
    __tablename__ = 'users'
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=False, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password = Column(Text, nullable=True)
    first_name = Column(String(50), nullable=True)
    last_name = Column(String(50), nullable=True)
    address = Column(String(255), nullable=True)
    state = Column(String(50), nullable=True)
    local_government = Column(String(50), nullable=True)
    phone_number = Column(String(15), nullable=True)
    time_created = Column(DateTime, default=func.now())
    is_staff = Column(Boolean, default=False)
    is_active = Column(Boolean, default=False)

    # Relationship to Order
    orders = relationship('Order', back_populates='user')
    addresses = relationship('Address', back_populates='user', cascade='all, delete-orphan')
    reviews = relationship('Review', back_populates='user', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"
    
    # # Add this inside the User class (usually near the bottom)
    # @validates('email')
    # def validate_email(self, key, email):
    #     """Ensure email contains an @ symbol and basic formatting"""
    #     if email is None:
    #         raise ValueError("Email cannot be null")
    #     if '@' not in email or '.' not in email.split('@')[-1]:
    #         raise ValueError("Invalid email address format")
    #     return email.lower().strip()  # Normalize email
    
    # # Other validations can be added for different fields
    # @validates('phone_number')
    # def validate_phone(self, key, phone):
    #     """Basic phone number validation"""
    #     if phone and not phone.startswith('+'):
    #         raise ValueError("Phone number must include country code")
    #     return phone

class Address(Base):
    __tablename__ = 'addresses'
    
    ADDRESS_TYPES = (
        ('HOME', 'home'),
        ('WORK', 'work'),
        ('OTHER', 'other')
    )
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    address_type = Column(String(20), default='HOME')  # Could use ChoiceType if preferred
    recipient_name = Column(String(100), nullable=False)
    street_address1 = Column(String(255), nullable=False)
    street_address2 = Column(String(255))
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    postal_code = Column(String(20), nullable=False)
    country = Column(String(100), nullable=False, default='United States')
    phone_number = Column(String(20))
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship('User', back_populates='addresses')
    orders = relationship('Order', back_populates='delivery_address')
    
    def __repr__(self):
        return f"<Address(id={self.id}, user_id={self.user_id}, city={self.city})>"
    
    @property
    def full_address(self):
        lines = [
            self.recipient_name,
            self.street_address1,
            self.street_address2,
            f"{self.city}, {self.state} {self.postal_code}",
            self.country
        ]
        return '\n'.join(filter(None, lines))
# class Order(Base):
#     PIZZA_FLAVOURS = (
#     ('MARGHERITA', 'Margherita'),
#     ('PEPPERONI', 'Pepperoni'),
#     ('VEGGIE', 'Veggie'),
#     ('BBQ_CHICKEN', 'BBQ Chicken'),
#     ('HAWAIIAN', 'Hawaiian'),
#     ('MEAT_FEAST', 'Meat Feast'),
#     ('FOUR_CHEESE', 'Four Cheese'),
#     ('BUFFALO', 'Buffalo'),
#     ('MUSHROOM', 'Mushroom'),
#     )

#     PIZZA_PRICES = {
#         'MARGHERITA': 10,
#         'PEPPERONI': 12,
#         'VEGGIE': 11,
#         'BBQ_CHICKEN': 13,
#         'HAWAIIAN': 12,
#         'MEAT_FEAST': 14,
#         'FOUR_CHEESE': 11,
#         'BUFFALO': 13,
#         'MUSHROOM': 10
#     }

#     ORDER_STATUSES = (
#         ('PENDING', 'pending'),
#         ('IN-TRANSIT', 'in-transit'),
#         ('DELIVERED', 'delivered'),
#         ('CANCELLED', 'cancelled')
#     )
#     PIZZA_SIZES = (
#         ('SMALL', 'small'),
#         ('MEDIUM', 'medium'),
#         ('LARGE', 'large'),
#         ('EXTRA-LARGE', 'extra-large')
#     )

#     __tablename__ = 'orders'
#     id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     quantity = Column(Integer, nullable=False)
#     order_status = Column(ChoiceType(choices=ORDER_STATUSES), default='PENDING')
#     pizza_size = Column(ChoiceType(choices=PIZZA_SIZES), default='SMALL')
#     flavour = Column(ChoiceType(choices=PIZZA_FLAVOURS), default='MARGHERITA')
#     user_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
#     total_cost = Column(Integer, nullable=False, default=0)
#     time_created = Column(DateTime, default=func.now())
#     user = relationship('User', back_populates='orders')

#     @property
#     def price(self):
#         # Use .code if using ChoiceType (can vary based on sqlalchemy-utils version)
#         flavour_code = self.flavour.code if hasattr(self.flavour, "code") else self.flavour
#         return self.PIZZA_PRICES.get(flavour_code, 0)

#     @property
#     def total(self):
#         return self.price * self.quantity
    
#     def __repr__(self):
#         return (
#             f"<Order(id={self.id}, user_id={self.customer_id}, "
#             f"quantity={self.quantity}, status={self.order_status}, "
#             f"size={self.pizza_size}, flavour={self.flavour})>"
#         )
    
#     @property
#     def pizza_size_code(self):
#         return self.pizza_size.code if self.pizza_size else None
#     @property
#     def flavour_code(self):
#         return self.flavour.code if self.flavour else None
#     @property
#     def order_status_code(self):
#         return self.order_status.code if self.order_status else None

# @event.listens_for(Order, 'before_insert')
# @event.listens_for(Order, 'before_update')
# def set_total_cost(mapper, connection, target):
#     target.total_cost = target.total

class Product(Base):
    __tablename__ = 'products'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    base_price = Column(Numeric(10, 2), nullable=False)
    category_id = Column(PG_UUID(as_uuid=True), ForeignKey('categories.id'))
    is_active = Column(Boolean, default=True)
    image_url = Column(String(255))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    category = relationship('Category', back_populates='products')
    inventory = relationship('Inventory', uselist=False, back_populates='product')
    variants = relationship('ProductVariant', back_populates='product',cascade='all, delete-orphan')

class ProductVariant(Base):
    __tablename__ = 'product_variants'

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(PG_UUID(as_uuid=True), ForeignKey('products.id'), nullable=False)
    name = Column(String(50))  # e.g., "Small", "Medium", "Large"
    price_modifier = Column(Numeric(10, 2), default=0.00)  # Additional price for this variant
    sku = Column(String(50), unique=True)
    
    product = relationship('Product', back_populates='variants')

class Category(Base):
    __tablename__ = 'categories'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), nullable=False, unique=True)
    description = Column(Text)
    parent_id = Column(PG_UUID(as_uuid=True), ForeignKey('categories.id'))
    
    products = relationship('Product', back_populates='category')
    children = relationship('Category')

class OrderItem(Base):
    __tablename__ = 'order_items'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(PG_UUID(as_uuid=True), ForeignKey('orders.id'), nullable=False)
    product_id = Column(PG_UUID(as_uuid=True), ForeignKey('products.id'), nullable=False)
    variant_id = Column(PG_UUID(as_uuid=True), ForeignKey('product_variants.id'))
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    notes = Column(Text)
    
    order = relationship('Order', back_populates='items')
    product = relationship('Product')
    variant = relationship('ProductVariant')

class Order(Base):
    __tablename__ = 'orders'
    
    ORDER_STATUSES = (
        ('PENDING', 'pending'),
        ('CONFIRMED', 'confirmed'),
        ('PREPARING', 'preparing'),
        ('IN_TRANSIT', 'in-transit'),
        ('DELIVERED', 'delivered'),
        ('CANCELLED', 'cancelled'),
        ('REFUNDED', 'refunded')
    )
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    status = Column(ChoiceType(choices=ORDER_STATUSES), default='PENDING')
    total_amount = Column(Numeric(10, 2), nullable=False)
    delivery_address_id = Column(PG_UUID(as_uuid=True), ForeignKey('addresses.id'))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    user = relationship('User', back_populates='orders')
    delivery_address = relationship('Address', back_populates='orders')
    payment = relationship('Payment', uselist=False, back_populates='order')
    items = relationship('OrderItem', back_populates='order',cascade='all, delete-orphan')

class Payment(Base):
    __tablename__ = 'payments'
    
    PAYMENT_STATUSES = (
        ('PENDING', 'pending'),
        ('COMPLETED', 'completed'),
        ('FAILED', 'failed'),
        ('REFUNDED', 'refunded'),
        ('PARTIALLY_REFUNDED', 'partially_refunded')
    )
    
    PAYMENT_METHODS = (
        ('CREDIT_CARD', 'credit_card'),
        ('DEBIT_CARD', 'debit_card'),
        ('PAYPAL', 'paypal'),
        ('STRIPE', 'stripe'),
        ('CASH_ON_DELIVERY', 'cash_on_delivery')
    )
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(PG_UUID(as_uuid=True), ForeignKey('orders.id'), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(ChoiceType(choices=PAYMENT_STATUSES), default='PENDING')
    method = Column(ChoiceType(choices=PAYMENT_METHODS), nullable=False)
    transaction_id = Column(String(100))  # From payment gateway
    gateway_response = Column(JSON)  # Raw response from payment processor
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    order = relationship('Order', back_populates='payment')
    refunds = relationship('Refund', back_populates='payment',cascade='all, delete-orphan')

class PaymentGateway(Base):
    __tablename__ = 'payment_gateways'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), nullable=False)  # e.g., "Stripe", "PayPal"
    is_active = Column(Boolean, default=True)
    config = Column(JSON)  # API keys, webhook URLs, etc.

class Refund(Base):
    __tablename__ = 'refunds'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_id = Column(PG_UUID(as_uuid=True), ForeignKey('payments.id'))
    amount = Column(Numeric(10, 2), nullable=False)
    reason = Column(Text)
    status = Column(String(20))  # PENDING, PROCESSED, FAILED
    created_at = Column(DateTime, default=func.now())
    
    payment = relationship('Payment')

class PaymentWebhookLog(Base):
    __tablename__ = 'payment_webhook_logs'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gateway_id = Column(PG_UUID(as_uuid=True), ForeignKey('payment_gateways.id'))
    payload = Column(JSON)
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())

class Inventory(Base):
    __tablename__ = 'inventory'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(PG_UUID(as_uuid=True), ForeignKey('products.id'), unique=True)
    quantity = Column(Integer, default=0)
    low_stock_threshold = Column(Integer, default=5)
    last_restocked = Column(DateTime)
    
    product = relationship('Product', back_populates='inventory')

class Cart(Base):
    __tablename__ = 'carts'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'), unique=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    items = relationship('CartItem', back_populates='cart', cascade='all, delete-orphan')
    user = relationship('User')

class CartItem(Base):
    __tablename__ = 'cart_items'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cart_id = Column(PG_UUID(as_uuid=True), ForeignKey('carts.id'))
    product_id = Column(PG_UUID(as_uuid=True), ForeignKey('products.id'))
    variant_id = Column(PG_UUID(as_uuid=True), ForeignKey('product_variants.id'))
    quantity = Column(Integer, default=1)
    
    cart = relationship('Cart', back_populates='items')
    product = relationship('Product')
    variant = relationship('ProductVariant')

class Review(Base):
    __tablename__ = 'reviews'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(PG_UUID(as_uuid=True), ForeignKey('products.id'))
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    rating = Column(Integer, nullable=False)  # 1-5
    comment = Column(Text)
    created_at = Column(DateTime, default=func.now())
    
    product = relationship('Product')
    user = relationship('User')

class Notification(Base):
    __tablename__ = 'notifications'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    notification_type = Column(String(50))  # 'order', 'payment', etc.
    reference_id = Column(PG_UUID(as_uuid=True))  # ID of related entity
    created_at = Column(DateTime, default=func.now())
    
    user = relationship('User')

