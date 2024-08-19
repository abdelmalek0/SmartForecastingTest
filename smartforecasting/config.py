from database import DatabaseHandler
from celery_config import make_celery
from redis_memory import RedisHandler
from utility import read_config
from constants import DB_CONFIG_FILENAME

class Config:
    @classmethod
    def initialize(cls, app):
        # Setup Redis and Celery
        cls.redis_handler = RedisHandler()
        cls.celery = make_celery(app)
        
        # Initialize the Database
        cls.db_config = read_config(DB_CONFIG_FILENAME)
        cls.database = DatabaseHandler(cls.db_config)
        
        cls.database.connect()
        cls.database.create_data_sources_table()
        cls.database.create_datasource_forecasting_table()
        app.app_context().push()
            