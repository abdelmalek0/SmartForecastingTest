# tasks.py
import time
import base64
import io
import pandas as pd
from celery import Celery
from celery.signals import worker_init, worker_shutdown
from structs.models import Training
from utility import *
from database import DatabaseHandler
from forecasting.auto_regression import AutoRegression
from forecasting.exponential_smoothing import ExponentialSmoothing
from forecasting.models import *
from forecasting.utility import *
from logging_config import logger

celery = Celery('tasks', broker='redis://localhost:6379/0', backend='redis://localhost:6379/0')

@celery.task(bind=True)
def process_file(self, file_data, datasource_id: int, config: dict):
    
    try:
        start_time = time.perf_counter()
        
        # Connect to Databases
        redis_handler = RedisHandler()
        database = DatabaseHandler(config)
        database.connect()
        logger.info(f'config: {database.config}')
        logger.info(f'ds id: {datasource_id}')
        
        datasource_str, datasource_index = search_data_source_by_id(
            datasource_id, redis_handler.get_all_data_sources()
        )
        
        # Decode the file data from base64
        file_data = base64.b64decode(file_data)

        # Convert the file data to a StringIO object for pandas
        file_io = io.StringIO(file_data.decode('utf-8'))

        # Read the CSV data into a DataFrame
        df = pd.read_csv(file_io)
        database.insert_dataframe(df, datasource_id)
        # database.disconnect()
        end_time = time.perf_counter()
        
        redis_handler.set_item(datasource_index, 'initialized', True)
        return f"Data insertion has been successfully completed in: {end_time - start_time} seconds"
    except Exception as e:
        raise Exception(e)
    
    return "Something went wrong!"

@celery.task(bind=True)
def process_training(self, training_data: str, datasource_id: int, config: dict, frequency: int):
    try:
        start_time = time.perf_counter()
        
        # Connect to Databases
        redis_handler = RedisHandler()
        training_data_object: Training = Training.parse_raw(training_data)
        database = DatabaseHandler(config)
        database.connect()
        logger.info(f'config: {database.config}')
        logger.info(f'ds id: {datasource_id}')
        
        datasource_str, datasource_index = search_data_source_by_id(
            datasource_id, redis_handler.get_all_data_sources()
        )

        df = database.get_all_data_for_datasource(datasource_id)
        logger.info(df)
        # database.disconnect()
        for algorithm in training_data_object.models:
            model = ForecastContext(algorithm, datasource_id)
            forecast_data = model.train(df, frequency)
            database.insert_forecasting_dataframe(forecast_data, datasource_id, algorithm.value)
        end_time = time.perf_counter()
        redis_handler.set_item(datasource_index, 'trained', True)
        return f"Training datasource has been successfully completed in: {end_time - start_time} seconds"
    except Exception as e:
        raise Exception(e)
    
    return "Something went wrong!"
