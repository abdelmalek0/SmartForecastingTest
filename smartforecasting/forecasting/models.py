from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import List, Tuple
from structs.enums import ForecastModel
import pandas as pd
import redis
import json
from logging_config import logger
from redis_memory import RedisHandler

class ForecastContext:

    def __init__(self, algorithm_type: ForecastModel, datasource_id: int):
        logger.info(algorithm_type)
        self.model = ForecastRegistry.get_model(algorithm_type, f'{datasource_id}_{algorithm_type.name}')

    def train(self, data: pd.DataFrame, frequency = '1D'):
        return self.model.train(data, frequency)

    def forecast(self, data: pd.DataFrame | None, date: date | datetime, steps: int = 1, frequency: str= '1D') -> pd.DataFrame | None:
        return self.model.forecast(data, date, steps, frequency)

    def set_model_params(self, model_params: list | None):
        self.model.set_model_params(model_params)

class ForecastStrategy(ABC):
    def __init__(self, vector_id: str) -> None:
        self.vector_id = vector_id
        redis_handler = RedisHandler()
        self.vector_db = redis_handler.r_db
        vector_str = self.vector_db.get(vector_id)
        logger.info(vector_id)
        if vector_str is not None:
            self.model_params = json.loads(vector_str)
        else:
            self.model_params = None

        logger.info(self.model_params)

    @abstractmethod
    def train(self, data, frequency = '1D') -> List[float]:
        pass

    @abstractmethod
    def forecast(self, data, date, steps = 1, frequency = '1D') -> pd.DataFrame | None:
        pass

    @abstractmethod
    def get_nb_lags_needed(self) -> int:
        pass

    def set_model_params(self, model_params: list | None):
        self.model_params = model_params


class ForecastRegistry:
    registry = {}

    @classmethod
    def register(cls, model_type: ForecastModel):
        def inner_wrapper(wrapped_class):
            cls.registry[model_type] = wrapped_class
            return wrapped_class
        return inner_wrapper

    @classmethod
    def get_model(cls, model_type: ForecastModel, vector_id: str):
        model_class = cls.registry.get(model_type)
        if not model_class:
            raise ValueError(f"No algorithm registered for {model_type}")
        return model_class(vector_id)
