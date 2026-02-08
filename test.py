from db_config.db_config import read_db_config


SECRET_KEY:str = read_db_config()['jwt_token']
ALGORITHM = "HS256"

print(SECRET_KEY)