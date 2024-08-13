from flask import Flask, request, jsonify, make_response
import uuid
from forecasting.models import ForecastContext
import pandas as pd
import time
import psycopg2
# from structs.data_point import DataPoint
from structs.enums import *
from structs.models import *
from utility import *
from database import DatabaseHandler
from pydantic import BaseModel, Field, ValidationError
from typing import List, Optional, Union
from async_tasks import process_file, process_training
from smartforecasting.celery_config import make_celery
from celery.result import AsyncResult
from datetime import date, datetime
import base64
import io
from structs.utility import *
from flasgger import swag_from
from flasgger import Swagger
from icecream import ic
from logging_config import logger
from redis_memory import RedisHandler
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

template = {
"swagger": "2.0",
"info": {
    "title": "SmartForecasting API",
    "description": "API designed to forecast product consumption and sales trends, empowering businesses to make data-driven decisions and stay ahead of the competition.",
    "version": "0.1.0"
},
}
swagger = Swagger(app, template=template)

app.config['UPLOAD_FOLDER'] = './csv_datasets/'
app.config['CONFIG_FILENAME'] = 'datasources.json'
app.config['DB_CONFIG_FILENAME'] = 'db.json'
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'

base_path = '/api/v1'
config = read_config(app.config['DB_CONFIG_FILENAME'])
database = DatabaseHandler(config)
redis_handler = RedisHandler()

celery = make_celery(app)
    
try:
    database.connect()
    database.create_data_sources_table()
    database.create_datasource_forecasting_table()
except Exception as e:
    raise e
    if database:
        database.disconnect()
    sys.exit()


@app.route(f'{base_path}/datasources', methods=['POST'])
def create_datasource():
    """
    file: ../docs/create_datasource.yaml
    """
    data = request.get_json()
    try:
        datasource_info = DataSourceInfo(**data)
    except ValidationError as e:
        logger.error(e.json())
        return jsonify(error = "Invalid JSON data"), 400

    datasource = DataSource(
        id = int(time.time()),
        datasource_info = datasource_info,
        training = Training(
            models = ['auto-regression']
        ),
        initialized = False,
        trained = False
    )
    
    redis_handler.add_data_source(datasource.model_dump())
    logger.info(redis_handler.get_all_data_sources())
    return jsonify({"id": datasource.id}), 200

@app.route(f'{base_path}/datasources', methods=['GET'])
def get_all_datasources():
    """
    file: ../docs/get_all_datasources.yaml
    """
    return jsonify(redis_handler.get_all_data_sources()), 200

@app.route(f'{base_path}/datasources/<datasource_id>', methods=['DELETE'])
def delete_datasource(datasource_id: int | str):
    """
    file: ../docs/delete_datasource.yaml
    """
    htmx = request.args.get('htmx')
    if (datasource_id := check_data_source_availability(datasource_id, redis_handler.get_all_data_sources())) == -1:
        return jsonify(error=f'No data source found with ID {datasource_id}'), 404
    # logger.info(datapoint)

    # app.config['DATA_SOURCES'].append(datasource.model_dump())
    try:
        logger.info('delete_datasource...')
        redis_handler.remove_data_source(datasource_id)
        database.delete_datasource(datasource_id)
        if not htmx:
            return jsonify(message=f'Data source with ID {datasource_id} has been deleted!'), 200
        else:
            return make_response('', 200)
    except Exception as e:
        logger.info(e)
        return jsonify(error=f'Could not delete data source with ID {datasource_id}'), 400 

@app.route(f'{base_path}/datasources/<datasource_id>/initialization', methods=['POST'])
def upload_file(datasource_id: str | int):
    """
    file: ../docs/upload_file.yaml
    """
    if 'file' not in request.files:
        return jsonify(error='No file part'), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify(error='No selected file'), 400

    if (datasource_id := check_data_source_availability(datasource_id, redis_handler.get_all_data_sources())) == -1:
        return jsonify(error=f'No data source found with ID {datasource_id}'), 404

    try:
        datasource_str, datasource_index = search_data_source_by_id(
            datasource_id, redis_handler.get_all_data_sources()
        )
        if not DataSource(**datasource_str).initialized:
            
            filename = file.filename
            file_data = file.read()
            file_data_base64 = base64.b64encode(file_data).decode('utf-8')
            process_file_task = process_file.apply_async(args=[file_data_base64, datasource_id, config])
            return jsonify({"task_id": process_file_task.id}), 202
        else:
            return jsonify(message='The datasource has already been set up.'), 200
    except Exception as e:
        return jsonify(error=f'Data initialization task couldn\'t be started: {e}'), 400

@app.route(f'{base_path}/datasources/<datasource_id>/datapoints', methods=['POST'])
def add_datapoints(datasource_id: str | int):
    """ file: ../docs/add_datapoints.yaml """
    data = request.get_json()
    
    if not isinstance(data, list):
        return jsonify(error="Invalid input: expected a list of datapoints"), 400
    
    valid_datapoints = []
    invalid_datapoints = []
    
    for item in data:
        try:
            datapoint = DataPoint(**item)
            valid_datapoints.append(datapoint)
        except ValidationError as e:
            invalid_datapoints.append({"data": item, "error": e.json()})
    
    if invalid_datapoints:
        return jsonify(error="Some datapoints are invalid", invalid_datapoints=invalid_datapoints), 400
    
    if (datasource_id := check_data_source_availability(datasource_id, redis_handler.get_all_data_sources())) == -1:
        return jsonify(error=f'No data source found with ID {datasource_id}'), 404
    
    try:
        skipped_datapoints = []
        for datapoint in valid_datapoints:
            if not database.add_data_point(datapoint, datasource_id):
                skipped_datapoints.append(skipped_datapoints)
        return jsonify(message=f'{len(valid_datapoints) - len(skipped_datapoints)} datapoints have been added to the database.')
    except Exception as e:
        print(e)
        return jsonify(error='Failed to add datapoints to the database.'), 500

@app.route(f'{base_path}/datasources/<datasource_id>/datapoints', methods=['GET'])
def get_datapoint(datasource_id: str | int):
    """
    file: ../docs/get_datapoint.yaml
    """
    # Extract query parameters
    ts = request.args.get('ts')
    if not ts:
        return jsonify(error='Missing required parameter: ts'), 400
    
    try:
        datapoint = DataPoint(ts= datetime.fromisoformat(ts), value=-1)
        logger.info(datapoint)
    except Exception as e:
        logger.error(e)
        return jsonify(error="Invalid timestamp format"), 400
    
    if (datasource_id := check_data_source_availability(datasource_id, redis_handler.get_all_data_sources())) == -1:
        return jsonify(error=f'No data source found with ID {datasource_id}'), 404
    logger.info(datapoint)
    try:
        datapoint.value = database.get_data_point(datasource_id, datapoint.ts)
        if datapoint.value == -1:
            raise Exception('No data point exists with that timestamp!')
        return jsonify(datapoint.model_dump())
    except Exception as e:
        logger.error(e)
        return jsonify(error='Failed to retrieve data point from the database.'), 500

@app.route(f'{base_path}/datasources/<datasource_id>/datapoints', methods=['PUT'])
def update_datapoint(datasource_id: str | int):
    """
    file: ../docs/update_datapoint.yaml
    """
    data = request.get_json()

    try:
        datapoint = DataPoint(**data)
        logger.info(datapoint)
    except ValidationError as e:
        logger.error(e.json())
        return jsonify(error = "Invalid JSON data"), 400

    if (datasource_id := check_data_source_availability(datasource_id, redis_handler.get_all_data_sources())) == -1:
        logger.info(redis_handler.get_all_data_sources())
        return jsonify(error=f'No data source found with ID {datasource_id}'), 404

    try:
        database.update_data_point(datapoint, datasource_id)
        return jsonify(message=f'Data point with timestamp {datapoint.ts} in data source ID {datasource_id} has been updated successfully.')
    except Exception as e:
        logger.error(e)
        return jsonify(error='Failed to update data point to the database.'), 500

@app.route(f'{base_path}/datasources/<datasource_id>/datapoints', methods=['DELETE'])
def delete_datapoint(datasource_id: str | int):
    """
    file: ../docs/delete_datapoint.yaml
    """
    # Extract the timestamp query parameter
    ts = request.args.get('ts')
    if not ts:
        return jsonify(error='Missing required parameter: ts'), 400
    
    try:
        datapoint = DataPoint(ts= datetime.fromisoformat(ts), value=-1)
        logger.info(datapoint)
    except Exception as e:
        logger.error(e)
        return jsonify(error="Invalid timestamp format"), 400

    # Check if the data source exists
    if (datasource_id := check_data_source_availability(datasource_id, redis_handler.get_all_data_sources())) == -1:
        return jsonify(error=f'No data source found with ID {datasource_id}'), 404

    try:
        # Attempt to delete the data point
        op = database.delete_data_point(datasource_id, datapoint.ts)
        if op == 1:
            return jsonify(message=f'Data point with timestamp {ts} in data source ID {datasource_id} has been deleted successfully.'), 200
        elif op == 0:
            return jsonify(error=f'No data point found for data source ID {datasource_id} at timestamp {ts}. Nothing was deleted.'), 404
        raise Exception("Operation failed!")
    except Exception as e:
        logger.error(f"An error occurred while deleting data point: {e}")
        return jsonify(error='Failed to delete data point from the database.'), 500


@app.route(f'{base_path}/datasources/<datasource_id>/datapoints/data', methods=['GET'])
def get_datapoints(datasource_id: str | int):
    """
    file: ../docs/get_datapoints.yaml
    """
    # Check if the data source exists
    if (datasource_id := check_data_source_availability(datasource_id, redis_handler.get_all_data_sources())) == -1:
        return jsonify(error=f'No data source found with ID {datasource_id}'), 404

    # Get query parameters
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    page = request.args.get('page')
    per_page = request.args.get('per_page')
    
    try:
        # Parse date filters using ISO 8601 format with 'Z' for UTC
        start_date = pd.to_datetime(start_date_str, format='%Y-%m-%dT%H:%M:%SZ', errors='coerce') if start_date_str else None
        end_date = pd.to_datetime(end_date_str, format='%Y-%m-%dT%H:%M:%SZ', errors='coerce') if end_date_str else None
        
        if (start_date_str and pd.isna(start_date)) or (end_date_str and pd.isna(end_date)):
            return jsonify(error='Invalid date format. Please use ISO 8601 format with "Z" (YYYY-MM-DDTHH:MM:SSZ).'), 400

        # Retrieve all data points for the given data source ID
        data_points_df: pd.DataFrame = database.get_all_data_for_datasource(datasource_id)
        
        if data_points_df.empty:
            return jsonify(message=f'No data points found for datasource ID {datasource_id}'), 404

        # Ensure 'ts' column is in datetime format
        data_points_df['ts'] = pd.to_datetime(data_points_df['ts'])

        # Apply date filters
        if start_date:
            data_points_df = data_points_df[data_points_df['ts'] >= start_date]
        if end_date:
            data_points_df = data_points_df[data_points_df['ts'] <= end_date]
        
        # Convert 'ts' to formatted string for JSON response
        data_points_df['ts'] = data_points_df['ts'].dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        data_points_df = data_points_df.sort_values(by='ts', ascending=False)
        
        if not page or not per_page:
            # Convert DataFrame to JSON
            data_points_json = data_points_df.to_dict(orient='records')

            return jsonify({'data': data_points_json}), 200
        
        page, per_page = int(page), int(per_page)
        
        # Paginate the data
        total_items = len(data_points_df)
        total_pages = (total_items - 1) // per_page + 1

        # Handle out-of-range pages
        if page > total_pages:
            return jsonify(error=f'Page {page} is out of range. Total pages: {total_pages}'), 404

        start_index = (page - 1) * per_page
        end_index = start_index + per_page
        paginated_df = data_points_df.iloc[start_index:end_index]

        # Convert DataFrame to JSON
        data_points_json = paginated_df.to_dict(orient='records')

        return jsonify({
            'data': data_points_json,
            'pagination': {
                'current_page': page,
                'total_pages': total_pages,
                'per_page': per_page,
                'total_items': total_items
            }
        }), 200 
    except Exception as e:
        logger.error(f"Failed to retrieve all data points: {e}")
        return jsonify(error='Failed to retrieve all data points from the database.'), 500

    
@app.route(f'{base_path}/datasources/<datasource_id>/datapoints/all', methods=['GET'])
def get_all_datapoints(datasource_id: str | int):
    """
    file: ../docs/get_all_datapoints.yaml
    """
    # Check if the data source exists
    if (datasource_id := check_data_source_availability(datasource_id, redis_handler.get_all_data_sources())) == -1:
        return jsonify(error=f'No data source found with ID {datasource_id}'), 404

    # Get query parameters
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    page = request.args.get('page')
    per_page = request.args.get('per_page')
    latest = request.args.get('latest')
    
    try:
        # Parse date filters using ISO 8601 format
        start_date = parse_date(start_date_str)
        end_date = parse_date(end_date_str)

        # Validate the parsed dates
        if (start_date_str and start_date is None) or (end_date_str and end_date is None):
            return jsonify(error='Invalid date format. Please use ISO 8601 format with "Z" (e.g., YYYY-MM-DDTHH:MM:SSZ, YYYY-MM-DDTHH:MM:SS.mmmZ, or YYYY-MM-DD).'), 400

        # Retrieve all data points for the given data source ID
        data_df: pd.DataFrame = database.get_all_data_for_datasource(datasource_id)
        forecasting_df: pd.DataFrame = database.get_forecasting_data_for_datasource(datasource_id)
        
        if not forecasting_df.empty:
            # Pivot forecasting_df to create separate columns for each algorithm
            pivot_forecasting_df = forecasting_df.pivot_table(
                index='ts',
                columns='algorithm',
                values='value'
            ).reset_index()

            # Rename the columns for clarity
            pivot_forecasting_df.columns.name = None
            # Rename columns if they exist
            rename_map = {
                'auto-regression': 'AutoReg',
                'exponential smoothing': 'ExpSmoothing'
            }

            # Check if columns exist before renaming
            pivot_forecasting_df.rename(columns={col: rename_map[col] 
                                                 for col in pivot_forecasting_df.columns 
                                                 if col in rename_map}, 
                                        inplace=True)
            for col in ['AutoReg', 'ExpSmoothing']:
                if col not in pivot_forecasting_df.columns:
                    pivot_forecasting_df[col] = ''

            # Reorder columns to have 'ts', 'AutoReg', 'ExpSmoothing'
            pivot_forecasting_df = pivot_forecasting_df[['ts', 'AutoReg', 'ExpSmoothing']]
        else:
            pivot_forecasting_df = pd.DataFrame(columns=['ts', 'AutoReg', 'ExpSmoothing'])

        # Merge pivoted DataFrame with data_df
        data_points_df = pd.merge(data_df, pivot_forecasting_df, on='ts', how='outer')
        data_points_df.fillna('', inplace=True)
        
        data_points_df['AutoReg'] = data_points_df['AutoReg'].apply(lambda x: int(x) if x else '')
        data_points_df['ExpSmoothing'] = data_points_df['ExpSmoothing'].apply(lambda x: int(x) if x else '')
        
        if data_points_df.empty:
            return jsonify({
                    'message': f'No data points found for datasource ID {datasource_id}',
                    'data': {}
                }), 404

        # Ensure 'ts' column is in datetime format
        data_points_df['ts'] = pd.to_datetime(data_points_df['ts'], utc=True)
         
        # Apply date filters
        if start_date or end_date:
            if start_date:
                datapoints_filtered = data_points_df[data_points_df['ts'] >= start_date]
            if end_date:
                datapoints_filtered = data_points_df[data_points_df['ts'] <= end_date]
        elif latest:
            datapoints_filtered = data_points_df.iloc[-int(latest):,:]
        else:
            datapoints_filtered = data_points_df.copy()
            
        # Convert 'ts' to formatted string for JSON response
        datapoints_filtered['ts'] = datapoints_filtered['ts'].dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        datapoints_filtered = datapoints_filtered.sort_values(by='ts', ascending=False)
        
        
        if not page or not per_page:
            # Convert DataFrame to JSON
            data_points_json = datapoints_filtered.to_dict(orient='records')

            return jsonify({
                                'data': data_points_json,                   
                                'minDate':data_points_df.iloc[-1,0],
                                'maxDate':data_points_df.iloc[0,0],
                            }), 200
        
        page, per_page = int(page), int(per_page)
        
        # Paginate the data
        total_items = len(datapoints_filtered)
        total_pages = (total_items - 1) // per_page + 1

        # Handle out-of-range pages
        if page > total_pages:
            return jsonify(error=f'Page {page} is out of range. Total pages: {total_pages}'), 404

        start_index = (page - 1) * per_page
        end_index = start_index + per_page
        paginated_df = datapoints_filtered.iloc[start_index:end_index]

        # Convert DataFrame to JSON
        data_points_json = paginated_df.to_dict(orient='records')

        return jsonify({
            'data': data_points_json,
            'minDate':data_points_df.iloc[-1,0],
            'maxDate':data_points_df.iloc[0,0],
            'pagination': {
                'current_page': page,
                'total_pages': total_pages,
                'per_page': per_page,
                'total_items': total_items
            }
        }), 200 
    except Exception as e:
        logger.error(f"Failed to retrieve all data points: {e}")
        return jsonify(error='Failed to retrieve all data points from the database.'), 500
    

@app.route(f'{base_path}/datasources/<datasource_id>/training', methods=['POST'])
def train_datasource(datasource_id: str | int):
    """
    file: ../docs/train_datasource.yaml
    """
    data = request.get_json()

    try:
        training_data = Training(**data)
        logger.info(training_data)
    except ValidationError as e:
        logger.error(e.json())
        return jsonify(error = "Invalid JSON data"), 400

    if (datasource_id := check_data_source_availability(datasource_id, redis_handler.get_all_data_sources())) == -1:
        return jsonify(error=f'No data source found with ID {datasource_id}'), 404

    try:
        datasource_str, datasource_index = search_data_source_by_id(
            datasource_id, redis_handler.get_all_data_sources()
        )
        datasource = DataSource( **(datasource_str))
        frequency = period_to_pandas_freq(datasource.datasource_info.period)
        logger.info(f'Training frequency: {frequency}')
        redis_handler.set_item(datasource_index, 'training', training_data.model_dump())
        logger.info(redis_handler.get_all_data_sources())
        task = process_training.apply_async(args=[training_data.json(), datasource_id, config, frequency])
        return jsonify({"task_id": task.id}), 202
    except Exception as e:
        return jsonify(error=f'Training task couldn\'t be started: {e}'), 400

@app.route(f'{base_path}/datasources/<datasource_id>/forecasting', methods=['GET'])
def get_forecast(datasource_id: str | int):
    """
    file: ../docs/get_forecast.yaml
    """
    start_time = time.perf_counter()

    # Instead of getting JSON data, get query parameters
    date = request.args.get('date')
    steps = request.args.get('steps')

    try:
        # Validate the input data
        forecasting_data = ForecastingData(date=date, steps=int(steps) if steps else 1)
        logger.info(forecasting_data)
    except ValidationError as e:
        return jsonify(error="Invalid query parameters"), 400

    if (datasource_id := check_data_source_availability(datasource_id, redis_handler.get_all_data_sources())) == -1:
        return jsonify(error=f'No data source found with ID {datasource_id}'), 404

    try:
        # Initialize the list to hold the forecast results for each algorithm
        forecast_results = []

        datasource = DataSource(
            **(search_data_source_by_id(datasource_id, redis_handler.get_all_data_sources())[0]))
        if datasource.trained: 
            if datasource is not None:
                frequency = period_to_pandas_freq(datasource.datasource_info.period)
                logger.info(f'frequency: {frequency}')

                for algorithm in datasource.training.models:
                    model = ForecastContext(algorithm, datasource_id)
                    if (lags := model.model.get_nb_lags_needed()) > 0:
                        data: pd.DataFrame = database.get_latest_data_points(datasource_id, lags)
                        if len(data) == 0:
                            raise Exception('No data points exist!')
                    else:
                        data = None

                    logger.info(data)
                    data_length = len(data)
                    result = model.forecast(data, forecasting_data.date, forecasting_data.steps, frequency)
                    logger.info(f'app:forecasting:result for {algorithm.value}: {result}')
                    if result is None:
                        return jsonify(error='Result is None'), 400 

                    database.insert_forecasting_dataframe(result.iloc[data_length:], datasource_id, algorithm.value)
                    result = result.iloc[-forecasting_data.steps:]
                    # Extract the dates and values from the result DataFrame
                    forecast_dates = result['ts'].dt.strftime('%Y-%m-%dT%H:%M:%SZ').tolist()
                    forecast_values = [max(0, x) for x in result['value'].tolist()]

                    # Append each algorithm's forecast to the results list
                    forecast_results.append({
                        'algorithm': algorithm.value,
                        'dates': forecast_dates,
                        'values': forecast_values
                    })
                    
            logger.info(f'forecast_results: {forecast_results}')
            end_time = time.perf_counter()
            response = jsonify({
                'forecasts': forecast_results,
                'operation_time': f'{end_time - start_time:.4f}s'
            })
            logger.info(f'response: {response}')
            return response, 200
        else:
            return jsonify(error='Training is required for this step!'), 400
    except Exception as e:
        logger.error(e)
        return jsonify(error='Failed to retrieve data point from the database.'), 500


@app.route(f'{base_path}/status/<task_id>', methods=['GET'])
def get_status(task_id):
    """
    file: ../docs/get_status.yaml
    """
    task = AsyncResult(task_id, app=celery)
    if task.state == 'PENDING':
        response = {"status": task.state}
    elif task.state == 'PROGRESS':
        response = {
            "status": "In Progress",
            "current": task.info.get('current', 0),
            "total": task.info.get('total', 1),
            "percent_complete": (task.info.get('current', 0) / task.info.get('total', 1)) * 100
        }
    else:
        response = {"status": task.state, "result": str(task.result)}
    return jsonify(response)
        
