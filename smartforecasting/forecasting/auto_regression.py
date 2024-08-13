from statsmodels.tsa.ar_model import AutoReg
from forecasting.models import *
from forecasting.utility import *
import numpy as np
import json
from typing import Final
from logging_config import logger

@ForecastRegistry.register(ForecastModel.AUTO_REGRESSION)
class AutoRegression(ForecastStrategy):
    MAX_LAGS: Final[int] = 15

    model_params = None

    def train(self, data, frequency = '1D'):
        logger.info('Training Data with Auto Regression ...')
        
        data.index = data['ts']
        data.index = pd.to_datetime(data.index)
        
        full_index = pd.date_range(start=data.index.min(), end=data.index.max(), freq=frequency)

        # Step 2: Reindex your DataFrame to this complete datetime index
        data = data.reindex(full_index)
        data['ts'] = data.index
        data.index.freq = frequency
        # Step 3: Interpolate or impute missing values
        data['value'] = data['value'].interpolate(method='linear')
        data = data.reset_index(drop=True)
        
        stationary_data, nb_diffs = auto_stationary(data['value'])
        stationary_data = pd.concat([pd.Series([data.iloc[0, -1]], index=[data.index[0]]), stationary_data])

        optimal_lag = find_best_lag_pvalues(stationary_data, self.MAX_LAGS)
        logger.info(optimal_lag)

        model = AutoReg(stationary_data, lags=optimal_lag).fit()
        self.model_params = [param for param in model.params]
        self.model_params.append(nb_diffs)

        self.vector_db.set(self.vector_id, json.dumps(self.model_params))
        
        
        
        start_index = len(model.params) # The index in df where the forecast starts
        end_index = len(data) - 1  # The index in df where the forecast ends
        
        forecast = list(model.predict(start=0, end=end_index))[start_index:]
        
        # Create a new DataFrame for the forecasted values
        forecast_data = pd.DataFrame({
            'ts': list(data.iloc[start_index:end_index + 1,0]),
            'value': forecast
        })
        logger.info(f'forecast_data: {forecast_data}')
        return forecast_data

    def forecast_next_value(self, stationary_data) -> float:
        if self.model_params is None:
            return -1

        # print('inside next value', (len(self.model_params) - 2) , len(stationary_data))
        assert (len(self.model_params) - 2) == len(stationary_data)
        # print(type(stationary_data))
        stationary_data_values = np.array(stationary_data)
        # print(stationary_data_values)

        y_t: float = self.model_params[0]
        # print('y_t: ', y_t)
        for i in range(len(stationary_data_values)):
            y_t += self.model_params[i+1] * stationary_data_values[i]
            # print('y_t: ', y_t)
        return y_t

    def forecast(self, data, date, steps = 1, frequency = '1D') -> pd.DataFrame | None:
        if self.model_params is None or data is None:
            return None

        # if date in the past
        if pd.Timestamp(date) < data['ts'].iloc[-1]:
            return None # the real values

        result = []
        start_range = data['ts'].iloc[-1]
        end_range = add_time(date, frequency, steps)
        # logger.info(start_range, end_range, frequency)
        for index, timestamp in enumerate(list(
            generate_range_datetime(start_range, end_range, frequency))):
            # logger.info(timestamp, data)
            stationary_data = make_stationary(data.iloc[index:, -1], lag=self.model_params[-1])
            # logger.info(stationary_data)
            value = self.forecast_next_value(stationary_data) + float(data.iloc[-1, -1])
            result.append(value)
            # logger.info(type(timestamp), type(value))
            new_row = pd.DataFrame({
                'ts': [timestamp],
                'value': [value]
            })
            # logger.info('result: ', result)
            data = pd.concat([data, new_row], ignore_index=True)
            # logger.info(data)
        return data

    def get_nb_lags_needed(self) -> int:
        if self.model_params is None:
            return -1
        # print(self.model_params)
        return len(self.model_params) - 2 + self.model_params[-1]
