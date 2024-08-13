from typing import List
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.ar_model import AutoReg
import pandas as pd
import numpy as np

def generate_range_datetime(start_date_str, end_date_str, frequency):
    # Convert strings to pandas datetime objects
    start_date = pd.to_datetime(start_date_str)
    end_date = pd.to_datetime(end_date_str)

    # Generate a date range with the specified frequency
    return pd.date_range(start=start_date, end=end_date, freq=frequency)[1:]

def add_time(base_date, frequency, steps=1):
    """
    Add time to a base date based on the specified frequency and steps.

    Parameters:
    - base_date (pd.Timestamp): The starting date.
    - frequency (str): Frequency of time increments ('2H', '7D', etc.).
    - steps (int): Number of times to add the frequency.

    Returns:
    - pd.Timestamp: New date after adding the specified time.
    """
    freq_type = frequency[-1]  # Get the last character, which indicates the frequency type
    freq_value = int(frequency[:-1])  # Get the numeric value of the frequency

    total_increment = freq_value * (steps - 1)
    
    if freq_type == 'T':
        return base_date + pd.DateOffset(minutes=total_increment)
    elif freq_type == 'H':
        return base_date + pd.DateOffset(hours=total_increment)
    elif freq_type == 'D':
        return base_date + pd.DateOffset(days=total_increment)
    elif freq_type == 'M':
        return base_date + pd.DateOffset(months=total_increment)
    elif freq_type == 'Y':
        return base_date + pd.DateOffset(years=total_increment)
    else:
        raise ValueError(f"Unsupported frequency: {frequency}")
    
def get_seasonal_periods(frequency):
    
    freq_type = frequency[-1]  # Get the last character, which indicates the frequency type
    freq_value = int(frequency[:-1])  # Get the numeric value of the frequency
    
    if freq_type == 'T':
        return 1440 // freq_value
    elif freq_type == 'H':
        return 24 // freq_value
    else:
        return None

def make_stationary(time_series, method='difference', lag=1):
    """
    Convert a time series to stationary using the specified method.

    Parameters:
    time_series (pd.Series): The time series data.
    method (str): The method to use ('difference' or 'log').
    lag (int): The lag to use for differencing (default is 1).

    Returns:
    pd.Series: The stationary time series.
    """

    if method == 'difference':
        stationary_series = time_series.diff(periods=lag).dropna()
    elif method == 'log':
        stationary_series = np.log(time_series).diff().dropna()
    else:
        raise ValueError("Unsupported method. Use 'difference' or 'log'.")

    return stationary_series

def auto_stationary(series: pd.Series) -> List:
    """
    Convert a time series to a stationary series by performing differencing if necessary.

    Args:
        series (pd.Series): The input time series data.

    Returns:
        List: A list where the first element is the stationary series and the second element is the number of differences applied.
    """
    # Perform the Augmented Dickey-Fuller test to check for stationarity
    result = adfuller(series)

    # Check if the series is stationary
    if result[1] < 0.05:
        # Series is stationary
        return [series, 0]
    else:
        # Series is non-stationary, perform differencing
        diff_series = series.diff().dropna()
        # Recursively apply differencing until stationarity is achieved
        result = auto_stationary(diff_series)
        result[1] += 1  # Increment the count of differences applied
        return result

def reconstruct_series_from_stationary(diff_series: pd.Series, n_diffs: int) -> pd.Series:
    """
    Reconstruct the original series from the stationary series by reversing differencing.

    Args:
        diff_series (pd.Series): The differenced (stationary) series.
        n_diffs (int): The number of times differencing was applied.

    Returns:
        pd.Series: The reconstructed series.
    """
    # Initialize the reconstructed series with the differenced series
    series = diff_series.copy()

    # Reverse differencing by cumulatively summing the series
    for _ in range(n_diffs):
        series = series.cumsum()

    return series

def find_best_lag_pvalues(data, max_lag, significance_level=0.05):
    best_lag = 0
    for lag in range(1, max_lag + 1):
        model = AutoReg(data, lags=lag)
        model_fitted = model.fit()
        pvalues = model_fitted.pvalues[1:]  # Exclude the intercept p-value
        if all(p < significance_level for p in pvalues):
            best_lag = lag
        else:
            break
    return best_lag
