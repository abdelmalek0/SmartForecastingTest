import numpy as np
from typing import List
from statsmodels.tsa.holtwinters import ExponentialSmoothing as ES
from forecasting.models import *
from forecasting.utility import *

@ForecastRegistry.register(ForecastModel.EXPONENTIAL_SMOOTHING)
class ExponentialSmoothing(ForecastStrategy):
    def train(self, data, frequency = '1D'):
        logger.info('Training Data with Exponential smoothing ...')
        original_data = data.copy()
        data.index = data['ts']
        data.index = pd.to_datetime(data.index)
        
        
        # Step 1: Generate a complete datetime index
        full_index = pd.date_range(start=data.index.min(), end=data.index.max(), freq=frequency)

        # Step 2: Reindex your DataFrame to this complete datetime index
        data = data.reindex(full_index)
        data['ts'] = data.index
        data.index.freq = frequency
        # Step 3: Interpolate or impute missing values
        data['value'] = data['value'].fillna(0.0)
        
        model = ES(data['value'], trend='add', seasonal='add', freq=frequency,
                   seasonal_periods=get_seasonal_periods(frequency)).fit()
        logger.info(f'Freq: {model.model.seasonal_periods}')
        
        self.model_params = {
            'alpha': model.params['smoothing_level'],
            'beta': model.params['smoothing_trend'],
            'gamma': model.params['smoothing_seasonal'],
            'last_level': model.level.iloc[-1],
            'last_trend': model.trend.iloc[-1],
            'last_season': model.season.iloc[-model.model.seasonal_periods:].tolist()
        }
        self.vector_db.set(self.vector_id, json.dumps(self.model_params))
        logger.info(f'model_params: {self.model_params}')
        
        start_index = 0 # The index in df where the forecast starts
        end_index = len(data) - 1  # The index in df where the forecast ends
        
        forecast = model.predict(start=start_index, end=end_index)
        
        # Create a new DataFrame for the forecasted values
        forecast_data = pd.DataFrame({
            'ts': forecast.index,
            'value': list(forecast)
        })
        
        forecast_data = forecast_data[forecast_data['ts'].isin(original_data['ts'])]
        forecast_data.loc[:, 'value'] = forecast_data['value'].fillna(0)
        forecast_data['value'] = forecast_data['value'].clip(lower=0)
        
        logger.info(len(forecast_data))
        logger.info(f'forecast_data: {forecast_data}')
        return forecast_data
    
    def update_model_params(self, model_params, new_data_point, trend_type='additive'):
        logger.info('Start updating model parameters:')
        alpha = model_params['alpha']
        beta = model_params['beta']
        gamma = model_params['gamma']

        last_level = model_params['last_level']
        last_trend = model_params['last_trend']
        last_season = model_params['last_season'][0]

        # Update the level, trend, and seasonal components
        if trend_type == 'additive':
            new_level = alpha * (new_data_point - last_season) + (1 - alpha) * (last_level + last_trend)
            new_trend = beta * (new_level - last_level) + (1 - beta) * last_trend
        elif trend_type == 'multiplicative':
            new_level = alpha * (new_data_point / last_season) + (1 - alpha) * (last_level + last_trend)
            new_trend = beta * (new_level / last_level) + (1 - beta) * last_trend

        new_season = gamma * (new_data_point - new_level) + (1 - gamma) * last_season

        model_params['last_level'] = new_level
        model_params['last_trend'] = new_trend
        model_params['last_season'].append(new_season)
        del model_params['last_season'][0]

        return model_params

    def forecast(self, data, date, steps = 1, frequency = '1D') -> pd.DataFrame | None:
        if self.model_params is None:
            return None
        
        model_params = self.model_params.copy()
        logger.info(f'forecast:model_params: {model_params}')

        # if date in the past
        if pd.Timestamp(date) < data['ts'].iloc[-1]:
            return None # the real values

        result = []
        start_range = data['ts'].iloc[-1]
        end_range = add_time(date, frequency, steps)
        logger.info(f'steps: {len(list(
            generate_range_datetime(start_range, end_range, frequency)))}')
        
        for index, timestamp in enumerate(list(
            generate_range_datetime(start_range, end_range, frequency))):
            logger.info(model_params)
            
            next_forecast = model_params['last_level'] + model_params['last_trend'] + model_params['last_season'][0]
            logger.info(f'next_forecast: {next_forecast}')
            model_params = self.update_model_params(model_params, next_forecast)
            result.append(next_forecast)
            
            new_row = pd.DataFrame({
                'ts': [timestamp],
                'value': [next_forecast]
            })
            # logger.info('result: ', result)
            data = pd.concat([data, new_row], ignore_index=True)
            
        data['value'] = data['value'].clip(lower=0)
        data = data[data['value'] != 0.0]
        return data

    def get_nb_lags_needed(self) -> int:
        return 1
