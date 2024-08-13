import pandas as pd
from enum import Enum

class PeriodType(str, Enum):
    MINUTE = 'minute'
    HOUR = 'hour'
    DAY = 'day'
    WEEK = 'week'
    MONTH = 'month'
    YEAR = 'year'
    
class ForecastModel(str, Enum):
    AUTO_REGRESSION = 'auto-regression'
    EXPONENTIAL_SMOOTHING = 'exponential smoothing'