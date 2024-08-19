from flask import Flask, request, jsonify, make_response, Blueprint
from forecasting.models import ForecastContext
import uuid
import pandas as pd
import time
from structs.enums import *
from structs.models import *
from utility import *
from pydantic import BaseModel, Field, ValidationError
from typing import List, Optional, Union
from async_tasks import process_file, process_training
from datetime import date, datetime
import base64
from structs.utility import *
from logging_config import logger
from constants import BASE_PATH
from config import Config
from threading import Thread

# Create a new Blueprint for the forecasting routes
bp = Blueprint('forecasting', __name__)

@bp.route(f'{BASE_PATH}/datasources/<datasource_id>/training', methods=['POST'])
def train_datasource(datasource_id: str | int):
    """
    file: ../../docs/train_datasource.yaml
    """
    data = request.get_json()

    # Validate the incoming JSON data against the Training model
    try:
        training_data = Training(**data)
        logger.info(f"Training data: {training_data}")
    except ValidationError as e:
        logger.error(f"Invalid JSON data: {e.json()}")
        return jsonify(error="Invalid JSON data"), 400

    # Check if the data source exists in Redis
    datasource_id = check_data_source_availability(datasource_id, Config.redis_handler.get_all_data_sources())
    if datasource_id == -1:
        return jsonify(error=f"No data source found with ID {datasource_id}"), 404

    try:
        # Retrieve the data source from Redis and extract relevant information
        datasource_str, datasource_index = search_data_source_by_id(datasource_id, Config.redis_handler.get_all_data_sources())
        datasource = DataSource(**datasource_str)
        frequency = period_to_pandas_freq(datasource.datasource_info.period)
        logger.info(f"Training frequency: {frequency}")

        # Update Redis with the new training data
        Config.redis_handler.set_item(datasource_index, 'training', training_data.model_dump())
        logger.info(f"Updated data sources: {Config.redis_handler.get_all_data_sources()}")

        # Start the training process asynchronously using Celery
        task = process_training.apply_async(args=[training_data.json(), datasource_id, Config.db_config, frequency])
        return jsonify({"task_id": task.id}), 202
    except Exception as e:
        logger.error(f"Training task couldn't be started: {e}")
        return jsonify(error=f"Training task couldn't be started: {e}"), 400

@bp.route(f'{BASE_PATH}/datasources/<datasource_id>/forecasting', methods=['GET'])
def get_forecast(datasource_id: str | int):
    """
    file: ../../docs/get_forecast.yaml
    """
    start_time = time.perf_counter()

    # Get query parameters for forecasting
    date_param = request.args.get('date')
    steps_param = request.args.get('steps')

    # Validate the query parameters using the ForecastingData model
    try:
        forecasting_data = ForecastingData(date=date_param, steps=int(steps_param) if steps_param else 1)
        logger.info(f"Forecasting data: {forecasting_data}")
    except ValidationError as e:
        logger.error(f"Invalid query parameters: {e.json()}")
        return jsonify(error="Invalid query parameters"), 400

    # Check if the data source exists in Redis
    datasource_id = check_data_source_availability(datasource_id, Config.redis_handler.get_all_data_sources())
    if datasource_id == -1:
        return jsonify(error=f"No data source found with ID {datasource_id}"), 404

    try:
        # Initialize a list to hold forecast results for each algorithm
        forecast_results = []

        # Retrieve the data source details from Redis
        datasource_str, _ = search_data_source_by_id(datasource_id, Config.redis_handler.get_all_data_sources())
        datasource = DataSource(**datasource_str)

        # Ensure the data source has been trained
        if not datasource.trained:
            return jsonify(error="Training is required for this step!"), 400

        frequency = period_to_pandas_freq(datasource.datasource_info.period)
        logger.info(f"Forecasting frequency: {frequency}")

        # Loop through each algorithm in the training models and generate forecasts
        for algorithm in datasource.training.models:
            model = ForecastContext(algorithm, datasource_id)
            lags_needed = model.model.get_nb_lags_needed()
            data = Config.database.get_latest_data_points(datasource_id, lags_needed) if lags_needed > 0 else None

            # Raise an error if no data points are available for forecasting
            if data is not None and data.empty:
                raise ValueError("No data points exist!")

            logger.info(f"Data for {algorithm.value}: {data}")
            data_length = len(data) if data is not None else 0

            # Generate the forecast and log the result
            result = model.forecast(data, forecasting_data.date, forecasting_data.steps, frequency)
            logger.info(f"Forecast result for {algorithm.value}: {result}")

            if result is None:
                return jsonify(error="Forecast result is None"), 400

            # Insert the forecast results into the database
            logger.info(f'{Config.database.cursor} {result.iloc[data_length:]}, {datasource_id}, {algorithm.value}')
            thread = Thread(target=lambda: [None 
                for index, total_rows in Config.database.insert_forecasting_dataframe(result.iloc[data_length:], datasource_id, algorithm.value)
                ]
            )
            thread.start()
            thread.join()
            result = result.iloc[-forecasting_data.steps:]

            # Prepare the forecast results for the response
            forecast_results.append({
                "algorithm": algorithm.value,
                "dates": result['ts'].dt.strftime('%Y-%m-%dT%H:%M:%SZ').tolist(),
                "values": [max(0, x) for x in result['value'].tolist()]
            })

        # Calculate operation time and prepare the response
        end_time = time.perf_counter()
        logger.info(f"Forecast results: {forecast_results}")
        return jsonify({
            "forecasts": forecast_results,
            "operation_time": f"{end_time - start_time:.4f}s"
        }), 200
    except Exception as e:
        logger.error(f"Error during forecasting: {e}")
        return jsonify(error="Failed to retrieve data point from the database."), 500

