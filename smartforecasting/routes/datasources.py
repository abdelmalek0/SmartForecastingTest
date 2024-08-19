from flask import Flask, request, jsonify, make_response, Blueprint
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

bp = Blueprint('datasources', __name__)

@bp.route(f'{BASE_PATH}/datasources', methods=['POST'])
def create_datasource():
    """
    file: ../../docs/create_datasource.yaml
    """
    logger.info('Creating a datasource ...')
    
    # Get JSON data from the request
    data = request.get_json()
    try:
        datasource_info = DataSourceInfo(**data)
    except ValidationError as e:
        logger.error(f'Invalid JSON data: {e}')
        return jsonify(error="Invalid JSON data"), 400
    
    # Create a new datasource instance
    datasource = DataSource(
        id=int(time.time()),
        datasource_info=datasource_info,
        training=Training(models=['auto-regression']),
        initialized=False,
        trained=False
    )
    
    try:
        # Add the datasource to Redis
        Config.redis_handler.add_data_source(datasource.model_dump())
    except Exception as e:
        logger.error(f'Failed to add datasource to Redis: {e}')
        return jsonify(error="Failed to create datasource"), 500

    logger.info(f'Datasource created successfully with ID: {datasource.id}')
    return jsonify({"id": datasource.id}), 201

@bp.route(f'{BASE_PATH}/datasources/all', methods=['GET'])
def get_all_datasources():
    """
    file: ../../docs/get_all_datasources.yaml
    """
    logger.info('Retrieving all datasources ...')
    
    try:
        # Retrieve all data sources from Redis
        datasources = Config.redis_handler.get_all_data_sources()
        logger.info(f'Successfully retrieved {len(datasources)} datasources')
        return jsonify(datasources), 200
    except Exception as e:
        logger.error(f'Failed to retrieve datasources: {e}')
        return jsonify(error="Failed to retrieve datasources"), 500

@bp.route(f'{BASE_PATH}/datasources/<datasource_id>', methods=['DELETE'])
def delete_datasource(datasource_id: Union[int, str]):
    """
    file: ../../docs/delete_datasource.yaml
    """
    logger.info(f'Deleting a datasource with ID: {datasource_id}')
    
    # Check if the request has an 'htmx' query parameter
    htmx = request.args.get('htmx')
    
    # Retrieve all data sources from Redis
    datasources = Config.redis_handler.get_all_data_sources()
    
    # Validate the datasource ID
    datasource_id = check_data_source_availability(datasource_id, datasources)
    
    if datasource_id == -1:
        logger.error(f'No data source found with this ID')
        return jsonify(error=f'No data source found with this ID'), 404
    
    try:
        # Remove the datasource from Redis and the database
        Config.redis_handler.remove_data_source(datasource_id)
        Config.database.delete_datasource(datasource_id)
        
        logger.info(f'Datasource with ID: {datasource_id} successfully deleted')
        
        # Return an appropriate response based on the 'htmx' parameter
        if not htmx:
            return jsonify(message=f'Data source with ID {datasource_id} has been deleted!'), 200
        else:
            return make_response('', 200)
    except Exception as e:
        logger.error(f'Failed to delete datasource with ID: {datasource_id}. Error: {e}')
        return jsonify(error=f'Could not delete data source with ID {datasource_id}'), 500

@bp.route(f'{BASE_PATH}/datasources/<datasource_id>/initialization', methods=['POST'])
def initialize_datasource(datasource_id: Union[str, int]):
    """
    file: ../../docs/initialize_datasource.yaml
    """
    logger.info(f'Initializing datasource with ID: {datasource_id}')
    
    # Check if a file is part of the request
    if 'file' not in request.files:
        logger.error('No file part in the request')
        return jsonify(error='No file part'), 400
    
    file = request.files['file']
    
    # Check if the file has a filename
    if file.filename == '':
        logger.error('No selected file')
        return jsonify(error='No selected file'), 400

    # Retrieve all data sources from Redis
    datasources = Config.redis_handler.get_all_data_sources()
    
    # Validate the datasource ID
    datasource_id = check_data_source_availability(datasource_id, datasources)
    
    if datasource_id == -1:
        logger.error(f'No data source found with ID: {datasource_id}')
        return jsonify(error=f'No data source found with ID {datasource_id}'), 404

    try:
        # Search for the datasource by ID
        datasource_str, datasource_index = search_data_source_by_id(datasource_id, datasources)
        datasource = DataSource(**datasource_str)
        
        if not datasource.initialized:
            # Read and encode the file data
            file_data = file.read()
            file_data_base64 = base64.b64encode(file_data).decode('utf-8')
            
            # Process the file asynchronously
            process_file_task = process_file.apply_async(args=[file_data_base64, datasource_id, Config.db_config])
            logger.info(f'Started file processing task with ID: {process_file_task.id}')
            return jsonify({"task_id": process_file_task.id}), 202
        else:
            logger.info(f'The datasource with ID: {datasource_id} is already initialized')
            return jsonify(message='The datasource has already been set up.'), 200
    except Exception as e:
        logger.error(f'Data initialization task couldn\'t be started: {e}')
        return jsonify(error=f'Data initialization task couldn\'t be started: {e}'), 500