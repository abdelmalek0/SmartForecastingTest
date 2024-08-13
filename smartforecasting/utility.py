import json
from structs.models import *
from structs.enums import *
import re
from logging_config import logger
from typing import Tuple
from dateutil import parser

def parse_date(date_str):
    """Parse a date string into a datetime object, ensuring UTC timezone."""
    if not date_str:
        return None

    try:
        # Parse with dateutil to handle various formats and ensure UTC
        parsed_date = parser.parse(date_str)

        # Ensure the date is timezone-aware with UTC
        if parsed_date.tzinfo is None:
            parsed_date = parsed_date.replace(tzinfo=pd.Timestamp.now().tzinfo)
        
        return parsed_date
    except (ValueError, TypeError):
        return None

def read_config(file_path: str) -> dict:
    """Read configuration from a JSON file."""
    with open(file_path, 'r') as file:
        config = json.load(file)
    return config

def save_config(file_path: str, config: dict):
    """Save configuration to a JSON file."""
    with open(file_path, 'w') as file:
        json.dump(config, file, indent=4)

def check_data_source_availability(ds_id: str | int, data_source_collection:dict):
    try:
        ds_id = int(ds_id)
        if search_data_source_by_id(ds_id, data_source_collection) is None:
            return -1
    except:
        logger.error('Converting id to integer was resulted in an error!')
        return -1

    return ds_id

def search_data_source_by_id(ds_id: int, data_source_collection: dict) -> Tuple[DataSource, int] | None:
    logger.info(data_source_collection)
    for index, data_source in enumerate(data_source_collection):
        logger.info(f'data_source id: {ds_id}')
        if data_source['id'] == ds_id:
            return (data_source, index)
    logger.info('No matching id!')
    return None

def convert_to_sql_datetime(timestamp: str) -> str:
    """
    Converts an ISO 8601 timestamp to SQL DATETIME format (YYYY-MM-DD HH:MM:SS).
    If the timestamp is already in SQL DATETIME format, no change is made.
    """
    # Regular expression to check if the timestamp is in ISO 8601 format
    iso8601_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(Z|[\+\-]\d{2}:\d{2})?$')
    
    # Check if the timestamp is in ISO 8601 format
    if iso8601_pattern.match(timestamp):
        # Convert ISO 8601 to SQL DATETIME
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # If it's already in SQL DATETIME format, return as is
    return timestamp
