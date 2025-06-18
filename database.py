from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker,declarative_base
from database_connection import connect_to_db
from src import logger

engine = connect_to_db.connect('pizzadeliverydb')[1]

Base=declarative_base()

# Session=sessionmaker()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# if connect_to_db.connect('pizzadeliverydb'):
#     logger.info(f"Connected to the pizzadeliverydb database successfully.")
# else:
#     logger.error("Failed to connect to the database.")
#     raise Exception("Database connection failed.")

# # engine=create_engine('postgresql://lamisplus:FmALa9PYGQUfyjq@localhost:5432/postgres', echo=True)