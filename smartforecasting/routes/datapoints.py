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

bp = Blueprint('datapoints', __name__)

@bp.route(f'{BASE_PATH}/datasources/<datasource_id>/datapoints', methods=['POST'])
def add_datapoints(datasource_id: str | int):
    """
    file: ../../docs/add_datapoints.yaml
    """
    # Get JSON data from the request
    data = request.get_json()
    
    # Validate that input data is a list
    if not isinstance(data, list):
        return jsonify(error="Invalid input: expected a list of datapoints"), 400
    
    valid_datapoints = []
    invalid_datapoints = []
    
    # Validate and separate valid and invalid datapoints
    for item in data:
        try:
            datapoint = DataPoint(**item)
            valid_datapoints.append(datapoint)
        except ValidationError as e:
            invalid_datapoints.append({"data": item, "error": e.json()})
    
    # # Return an error if there are invalid datapoints
    # if invalid_datapoints:
    #     return jsonify(error="Some datapoints are invalid", invalid_datapoints=invalid_datapoints), 400
    
    # Check if the data source is available
    if (datasource_id := check_data_source_availability(datasource_id, Config.redis_handler.get_all_data_sources())) == -1:
        return jsonify(error=f'No data source found with ID {datasource_id}'), 404
    
    try:
        skipped_datapoints = []
        # Add valid datapoints to the database
        for datapoint in valid_datapoints:
            if not Config.database.add_data_point(datapoint, datasource_id):
                skipped_datapoints.append(datapoint)
        return jsonify(message=f'{len(valid_datapoints) - len(skipped_datapoints)} datapoints have been added to the database.')
    except Exception as e:
        print(e)
        return jsonify(error='Failed to add datapoints to the database.'), 500

@bp.route(f'{BASE_PATH}/datasources/<datasource_id>/datapoints', methods=['GET'])
def get_datapoint(datasource_id: str | int):
    """
    file: ../../docs/get_datapoint.yaml
    """
    # Extract and validate the timestamp query parameter
    ts = request.args.get('ts')
    if not ts:
        return jsonify(error='Missing required parameter: ts'), 400
    
    try:
        datapoint = DataPoint(ts=datetime.fromisoformat(ts), value=-1)
        logger.info(datapoint)
    except Exception as e:
        logger.error(e)
        return jsonify(error="Invalid timestamp format"), 400
    
    # Check if the data source is available
    if (datasource_id := check_data_source_availability(datasource_id, Config.redis_handler.get_all_data_sources())) == -1:
        return jsonify(error=f'No data source found with ID {datasource_id}'), 404
    
    try:
        # Retrieve the value for the specified timestamp
        datapoint.value = Config.database.get_data_point(datasource_id, datapoint.ts)
        if datapoint.value == -1:
            raise Exception('No data point exists with that timestamp!')
        return jsonify(datapoint.model_dump())
    except Exception as e:
        logger.error(e)
        return jsonify(error='Failed to retrieve data point from the database.'), 500

@bp.route(f'{BASE_PATH}/datasources/<datasource_id>/datapoints', methods=['PUT'])
def update_datapoint(datasource_id: str | int):
    """
    file: ../../docs/update_datapoint.yaml
    """
    # Get JSON data from the request
    data = request.get_json()

    try:
        datapoint = DataPoint(**data)
        logger.info(datapoint)
    except ValidationError as e:
        logger.error(e.json())
        return jsonify(error="Invalid JSON data"), 400

    # Check if the data source is available
    if (datasource_id := check_data_source_availability(datasource_id, Config.redis_handler.get_all_data_sources())) == -1:
        # logger.info(redis_handler.get_all_data_sources())
        return jsonify(error=f'No data source found with ID {datasource_id}'), 404

    try:
        # Update the datapoint in the database
        Config.database.update_data_point(datapoint, datasource_id)
        return jsonify(message=f'Data point with timestamp {datapoint.ts} in data source ID {datasource_id} has been updated successfully.')
    except Exception as e:
        logger.error(e)
        return jsonify(error='Failed to update data point in the database.'), 500

@bp.route(f'{BASE_PATH}/datasources/<datasource_id>/datapoints', methods=['DELETE'])
def delete_datapoint(datasource_id: str | int):
    """
    file: ../../docs/delete_datapoint.yaml
    """
    # Extract the timestamp query parameter
    ts = request.args.get('ts')
    if not ts:
        return jsonify(error='Missing required parameter: ts'), 400
    
    try:
        datapoint = DataPoint(ts=datetime.fromisoformat(ts), value=-1)
        logger.info(datapoint)
    except Exception as e:
        logger.error(e)
        return jsonify(error="Invalid timestamp format"), 400

    # Check if the data source is available
    if (datasource_id := check_data_source_availability(datasource_id, Config.redis_handler.get_all_data_sources())) == -1:
        return jsonify(error=f'No data source found with ID {datasource_id}'), 404

    try:
        # Attempt to delete the datapoint from the database
        op = Config.database.delete_data_point(datasource_id, datapoint.ts)
        if op == 1:
            return jsonify(message=f'Data point with timestamp {ts} in data source ID {datasource_id} has been deleted successfully.'), 200
        elif op == 0:
            return jsonify(error=f'No data point found for data source ID {datasource_id} at timestamp {ts}. Nothing was deleted.'), 404
        raise Exception("Operation failed!")
    except Exception as e:
        logger.error(f"An error occurred while deleting data point: {e}")
        return jsonify(error='Failed to delete data point from the database.'), 500

@bp.route(f'{BASE_PATH}/datasources/<datasource_id>/datapoints/data', methods=['GET'])
def get_datapoints(datasource_id: str | int):
    """
    file: ../../docs/get_datapoints.yaml
    """
    # Check if the data source is available
    if (datasource_id := check_data_source_availability(datasource_id, Config.redis_handler.get_all_data_sources())) == -1:
        return jsonify(error=f'No data source found with ID {datasource_id}'), 404

    # Extract and parse query parameters
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    page = request.args.get('page')
    per_page = request.args.get('per_page')
    
    try:
        # Parse date filters using ISO 8601 format with 'Z' for UTC
        start_date = pd.to_datetime(start_date_str, format='%Y-%m-%dT%H:%M:%SZ', errors='coerce') if start_date_str else None
        end_date = pd.to_datetime(end_date_str, format='%Y-%m-%dT%H:%M:%SZ', errors='coerce') if end_date_str else None
        
        # Validate date formats
        if (start_date_str and pd.isna(start_date)) or (end_date_str and pd.isna(end_date)):
            return jsonify(error='Invalid date format. Please use ISO 8601 format with "Z" (YYYY-MM-DDTHH:MM:SSZ).'), 400

        # Retrieve all data points for the datasource
        data_points_df: pd.DataFrame = Config.database.get_all_data_for_datasource(datasource_id)
        
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
        
        # Handle pagination
        if not page or not per_page:
            data_points_json = data_points_df.to_dict(orient='records')
            return jsonify({'data': data_points_json}), 200
        
        page, per_page = int(page), int(per_page)
        
        total_items = len(data_points_df)
        total_pages = (total_items - 1) // per_page + 1

        # Handle out-of-range pages
        if page > total_pages:
            return jsonify(error=f'Page {page} is out of range. Total pages: {total_pages}'), 404

        start_index = (page - 1) * per_page
        end_index = start_index + per_page

        paginated_data = data_points_df.iloc[start_index:end_index].to_dict(orient='records')

        # Return paginated results
        return jsonify({
            'total_items': total_items,
            'total_pages': total_pages,
            'current_page': page,
            'per_page': per_page,
            'data': paginated_data
        }), 200

    except Exception as e:
        logger.error(f"An error occurred while retrieving data points: {e}")
        return jsonify(error='Failed to retrieve data points from the database.'), 500

@bp.route(f'{BASE_PATH}/datasources/<datasource_id>/datapoints/all', methods=['GET'])
def get_all_datapoints(datasource_id: str | int):
    """
    file: ../../docs/get_all_datapoints.yaml
    """
    # Check if the data source exists
    if (datasource_id := check_data_source_availability(datasource_id, Config.redis_handler.get_all_data_sources())) == -1:
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
        data_df: pd.DataFrame = Config.database.get_all_data_for_datasource(datasource_id)
        forecasting_df: pd.DataFrame = Config.database.get_forecasting_data_for_datasource(datasource_id)
        
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
