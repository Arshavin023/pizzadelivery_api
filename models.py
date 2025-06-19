from database import Base
import uuid
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import Column, ForeignKey,BigInteger, Integer, Boolean, Text, String, DateTime
from sqlalchemy_utils.types import ChoiceType
from datetime import datetime
from sqlalchemy.orm import relationship
from sqlalchemy import event  
from sqlalchemy import func

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
    orders = relationship('Order', back_populates='user', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"


class Order(Base):
    PIZZA_FLAVOURS = (
    ('MARGHERITA', 'Margherita'),
    ('PEPPERONI', 'Pepperoni'),
    ('VEGGIE', 'Veggie'),
    ('BBQ_CHICKEN', 'BBQ Chicken'),
    ('HAWAIIAN', 'Hawaiian'),
    ('MEAT_FEAST', 'Meat Feast'),
    ('FOUR_CHEESE', 'Four Cheese'),
    ('BUFFALO', 'Buffalo'),
    ('MUSHROOM', 'Mushroom'),
    )

    PIZZA_PRICES = {
        'MARGHERITA': 10,
        'PEPPERONI': 12,
        'VEGGIE': 11,
        'BBQ_CHICKEN': 13,
        'HAWAIIAN': 12,
        'MEAT_FEAST': 14,
        'FOUR_CHEESE': 11,
        'BUFFALO': 13,
        'MUSHROOM': 10
    }

    ORDER_STATUSES = (
        ('PENDING', 'pending'),
        ('IN-TRANSIT', 'in-transit'),
        ('DELIVERED', 'delivered'),
        ('CANCELLED', 'cancelled')
    )
    PIZZA_SIZES = (
        ('SMALL', 'small'),
        ('MEDIUM', 'medium'),
        ('LARGE', 'large'),
        ('EXTRA-LARGE', 'extra-large')
    )

    __tablename__ = 'orders'
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quantity = Column(Integer, nullable=False)
    order_status = Column(ChoiceType(choices=ORDER_STATUSES), default='PENDING')
    pizza_size = Column(ChoiceType(choices=PIZZA_SIZES), default='SMALL')
    flavour = Column(ChoiceType(choices=PIZZA_FLAVOURS), default='MARGHERITA')
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    total_cost = Column(Integer, nullable=False, default=0)
    time_created = Column(DateTime, default=func.now())
    user = relationship('User', back_populates='orders')

    @property
    def price(self):
        # Use .code if using ChoiceType (can vary based on sqlalchemy-utils version)
        flavour_code = self.flavour.code if hasattr(self.flavour, "code") else self.flavour
        return self.PIZZA_PRICES.get(flavour_code, 0)

    @property
    def total(self):
        return self.price * self.quantity
    
    def __repr__(self):
        return (
            f"<Order(id={self.id}, user_id={self.customer_id}, "
            f"quantity={self.quantity}, status={self.order_status}, "
            f"size={self.pizza_size}, flavour={self.flavour})>"
        )
    
    @property
    def pizza_size_code(self):
        return self.pizza_size.code if self.pizza_size else None
    @property
    def flavour_code(self):
        return self.flavour.code if self.flavour else None
    @property
    def order_status_code(self):
        return self.order_status.code if self.order_status else None

@event.listens_for(Order, 'before_insert')
@event.listens_for(Order, 'before_update')
def set_total_cost(mapper, connection, target):
    target.total_cost = target.total