from database_connection.database import Base, engine
from Models.models import User, Order, Address, Review, Payment, PaymentGateway, Refund
import asyncio

async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created successfully")

if __name__ == "__main__":
    asyncio.run(init_models())