import redis
import json
from logging_config import logger

class RedisHandler:
    def __init__(self, host='localhost', port=6379, db=0):
        self.r_db = redis.Redis(host=host, port=port, db=db)
        logger.info('Redis instance has been initialized!')

    def add_data_source(self, data_source_dict):
        """
        Add a data source to the Redis list.

        :param data_source_dict: Dictionary containing the data source information.
        """
        # Convert the dictionary to a JSON string
        json_item = json.dumps(data_source_dict)
        
        # Append the JSON string to the Redis list
        self.r_db.rpush('data_sources', json_item)

    def get_all_data_sources(self):
        """
        Retrieve all data sources from the Redis list.

        :return: List of data source dictionaries.
        """
        # Get all items from the Redis list
        json_items = self.r_db.lrange('data_sources', 0, -1)
        
        # Convert JSON strings back to dictionaries
        return [json.loads(item) for item in json_items]

    def set_item(self, index, key, new_value):
        """
        Update a specific key in a data source at the given index.

        :param index: Index of the data source in the Redis list.
        :param key: Key to be updated in the data source.
        :param new_value: New value for the specified key.
        :raises IndexError: If the data source is not found at the specified index.
        :raises KeyError: If the specified key is not found in the data source.
        """
        # Get the item at the specified index
        json_item = self.r_db.lindex('data_sources', index)
        
        if json_item is None:
            raise IndexError("Data source not found at the specified index")
        
        # Convert JSON string to dictionary
        data_source = json.loads(json_item)
        
        # Update the specified key with the new value
        if key not in data_source:
            raise KeyError(f"Key '{key}' not found in the data source")
        
        data_source[key] = new_value
        
        # Convert the updated dictionary back to a JSON string
        updated_json_item = json.dumps(data_source)
        
        # Replace the item in the Redis list
        self.r_db.lset('data_sources', index, updated_json_item)
    
    def remove_data_source(self, data_source_id):
        """
        Remove a data source from the Redis list based on its ID.

        :param data_source_id: ID of the data source to be removed.
        :raises ValueError: If the data source with the given ID is not found.
        """
        # Get all items from the Redis list
        json_items = self.r_db.lrange('data_sources', 0, -1)
        
        # Find the index of the item with the specified ID
        for index, json_item in enumerate(json_items):
            data_source = json.loads(json_item)
            
            if data_source.get('id') == data_source_id:
                # Remove the item from the Redis list
                self.r_db.lrem('data_sources', 1, json_item)
                logger.info(f"Removed data source with ID: {data_source_id}")
                return
        
        raise ValueError(f"Data source with ID {data_source_id} not found.")