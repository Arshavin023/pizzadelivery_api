from database import Session, Base, engine
from models import Customer, Order

Base.metadata.create_all(bind=engine)