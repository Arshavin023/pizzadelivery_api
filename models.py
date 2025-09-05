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
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password = Column(Text, nullable=True)
    first_name = Column(String(50), nullable=True)
    last_name = Column(String(50), nullable=True)
    phone_number = Column(String(15), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    is_staff = Column(Boolean, default=False)
    is_active = Column(Boolean, default=False)

    # Relationship to Order, Address, Review
    orders = relationship('Order', back_populates='user')
    addresses = relationship('Address', back_populates='user', cascade='all, delete-orphan')
    reviews = relationship('Review', back_populates='user', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"

class Address(Base):
    __tablename__ = 'addresses'
    # __table_args__ = {
    #     'postgresql_partition_by': 'LIST (country)'
    # }
    ADDRESS_TYPES = (
        ('HOME', 'home'),
        ('WORK', 'work'),
        ('OTHER', 'other')
    )
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    address_type = Column(ChoiceType(choices=ADDRESS_TYPES), default='HOME')  # Could use ChoiceType if preferred
    recipient_name = Column(String(100), nullable=True)
    street_address1 = Column(String(255), nullable=True)
    street_address2 = Column(String(255))
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(100), nullable=True)
    full_address = Column(Text, nullable=True)  # Optional, can be computed
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
            self.street_address1,',',
            self.street_address2,
            f"{self.postal_code}, {self.city}, {self.state} state,",
            self.country
        ]
        return ' '.join(filter(None, lines))


class Product(Base):
    __tablename__ = 'products'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=True)
    description = Column(Text)
    base_price = Column(Numeric(10, 2), nullable=True)
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
    created_at = Column(DateTime, default=func.now()) # Added for consistency
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now()) # Added for consistency

    product = relationship('Product', back_populates='variants')

class Category(Base):
    __tablename__ = 'categories'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), nullable=False, unique=True)
    description = Column(Text)
    parent_id = Column(PG_UUID(as_uuid=True), ForeignKey('categories.id'))
    created_at = Column(DateTime, default=func.now()) # Added for consistency
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now()) # Added for consistency

    products = relationship('Product', back_populates='category',cascade='all, delete-orphan')
    children = relationship('Category', remote_side=[id]) # Corrected remote_side for self-referencing

class OrderItem(Base):
    __tablename__ = 'order_items'
    __table_args__ = (
        {'postgresql_partition_by': 'HASH (order_id)'}
    )
    # The rest of your existing columns...
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(PG_UUID(as_uuid=True), ForeignKey('orders.id'), nullable=False)
    product_id = Column(PG_UUID(as_uuid=True), ForeignKey('products.id'), nullable=False)
    variant_id = Column(PG_UUID(as_uuid=True), ForeignKey('product_variants.id'))
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    notes = Column(Text)
    
    # Relationships
    order = relationship('Order', back_populates='items')
    product = relationship('Product')
    variant = relationship('ProductVariant')


class Order(Base):
    __tablename__ = 'orders'
    __table_args__ = (
        {'postgresql_partition_by': 'RANGE (created_at)'}
    )

    ORDER_STATUSES = (
        ('PENDING', 'pending'),
        ('CONFIRMED', 'confirmed'),
        ('PREPARING', 'preparing'),
        ('IN_TRANSIT', 'in-transit'),
        ('DELIVERED', 'delivered'),
        ('CANCELLED', 'cancelled'),
        ('REFUNDED', 'refunded')
    )

    # The rest of your existing columns...
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    status = Column(ChoiceType(choices=ORDER_STATUSES), default='PENDING')
    total_amount = Column(Numeric(10, 2), nullable=False)
    delivery_address_id = Column(PG_UUID(as_uuid=True), ForeignKey('addresses.id'))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship('User', back_populates='orders')
    delivery_address = relationship('Address', back_populates='orders')
    payment = relationship('Payment', uselist=False, back_populates='order')
    items = relationship('OrderItem', back_populates='order',cascade='all, delete-orphan')


class Payment(Base):
    __tablename__ = 'payments'
    __table_args__ = (
        {'postgresql_partition_by': 'RANGE (created_at)'}
    )

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

    # The rest of your existing columns...
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(PG_UUID(as_uuid=True), ForeignKey('orders.id'), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(ChoiceType(choices=PAYMENT_STATUSES), default='PENDING')
    method = Column(ChoiceType(choices=PAYMENT_METHODS), nullable=False)
    transaction_id = Column(String(100))
    gateway_response = Column(JSON)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
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
    __table_args__ = (
        {'postgresql_partition_by': 'HASH (product_id)'}
    )
    # The rest of your existing columns...
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(PG_UUID(as_uuid=True), ForeignKey('products.id'))
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    rating = Column(Integer, nullable=False)
    comment = Column(Text)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    product = relationship('Product')
    user = relationship('User')

class Notification(Base):
    __tablename__ = 'notifications'
    __table_args__ = (
        {'postgresql_partition_by': 'HASH (user_id)'}
    )
    # The rest of your existing columns...
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    notification_type = Column(String(50))
    reference_id = Column(PG_UUID(as_uuid=True))
    created_at = Column(DateTime, default=func.now())
    
    # Relationship
    user = relationship('User')

