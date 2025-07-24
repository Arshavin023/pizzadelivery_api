# database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from db_config.db_config import read_db_config
from sqlalchemy.orm import sessionmaker,declarative_base

Base=declarative_base()
db_config = read_db_config()

host = db_config['webapp_host']
user = db_config['webapp_username']
password = db_config['webapp_password']
port = db_config['webapp_port']

# DATABASE_URL = f"postgresql+asyncpg://{user}:{password}@localhost/pizzadeliverydb"
DATABASE_URL = f"postgresql+asyncpg://{user}:{password}@localhost/abacha_delivery_db"

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def get_async_db():
    async with AsyncSessionLocal() as session:
        yield session
