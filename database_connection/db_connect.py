import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import psycopg2
from psycopg2.extras import Json
import sqlalchemy
from sqlalchemy import create_engine, JSON, Integer, String, Float, DateTime, Boolean
from sqlalchemy.dialects.postgresql import JSONB
import configparser
from db_config.db_config import read_db_config

from src import logger

class DatabaseConnection:
    def __init__(self, db_config:dict
                #  host:str, database:str, user:str, password:str, port:int
                 ):
        self.host = db_config['webapp_host']
        self.user = db_config['webapp_username']
        self.password = db_config['webapp_password']
        self.port = db_config['webapp_port']


    def connect(self, database:str):
        '''
        Establishes a connection to the specified PostgreSQL database.
        Parameters:
        - database (str): The name of the database to connect to.
        Returns:
        - conn (psycopg2.connection): The connection object.
        - engine (sqlalchemy.engine.base.Engine): The SQLAlchemy engine object.
        Raises:
        - Exception: If connection to the database fails.
        '''
        db_params = {'host': self.host, 'database': database, 'user': self.user,
                      'password': self.password,'port': self.port,}
        try:
            conn = psycopg2.connect(**db_params)
            engine = create_engine(f'postgresql://{db_params["user"]}:{db_params["password"]}@{db_params["host"]}:{db_params["port"]}/{db_params["database"]}',
                                   echo=True)
            return [conn, engine]
        
        except Exception as e:
            logger.exception(e)
            raise e

db_param = read_db_config()
connect_to_db = DatabaseConnection(db_param)
# database_name = db_param['webapp_database_name']
# if connect_to_db.connect('pizzadeliverydb'):
#     logger.info(f"Connected to the {database_name} database successfully.")
# else:
#     logger.error("Failed to connect to the database.")
#     raise Exception("Database connection failed.")

