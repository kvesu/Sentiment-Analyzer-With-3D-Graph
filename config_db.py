import os
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

def get_mysql_engine(echo: bool = False):
    user = os.getenv("MYSQL_USER")
    pwd  = os.getenv("MYSQL_PASSWORD")
    host = os.getenv("MYSQL_HOST", "127.0.0.1")
    port = os.getenv("MYSQL_PORT", "3306")
    db   = os.getenv("MYSQL_DB")
    url  = f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{db}?charset=utf8mb4"
    return create_engine(url, echo=echo, pool_pre_ping=True, pool_recycle=3600)
