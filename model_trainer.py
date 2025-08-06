import pandas as pd
import numpy as np
import xgboost as xgb
from prophet import Prophet
from statsmodels.tsa.arima.model import ARIMA
from sklearn.metrics import mean_squared_error, mean_absolute_percentage_error

def _calculate_metrics(y_true, y_pred):
    """Calculates RMSE and MAPE."""
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mape = mean_absolute_percentage_error(y_true, y_pred)
    return rmse, mape

def _create_features(df, value_col):
    """Creates time series features from datetime index."""
    df['hour'] = df.index.hour
    df['dayofweek'] = df.index.dayofweek
    df['quarter'] = df.index.quarter
    df['month'] = df.index.month
    df['year'] = df.index.year
    df['dayofyear'] = df.index.dayofyear
    df['dayofmonth'] = df.index.day
    df['weekofyear'] = df.index.isocalendar().week.astype(int)
    X = df.drop(columns=[value_col])
    y = df[value_col]
    return X, y

def train_and_predict(df, model_name, params, forecast_horizon, value_col):
    """
    Trains a selected model, makes predictions, and evaluates the model.

    Args:
        df (pd.DataFrame): The preprocessed input DataFrame with datetime index.
        model_name (str): The name of the model to train ('XGBoost', 'Prophet', 'ARIMA').
        params (dict): A dictionary of hyperparameters for the model.
        forecast_horizon (int): The number of periods to forecast into the future.
        value_col (str): The name of the target value column.

    Returns:
        dict: A dictionary containing results.
    """

    # 1. Data Splitting (80-20 split)
    split_point = int(len(df) * 0.8)
    train_df = df.iloc[:split_point]
    test_df = df.iloc[split_point:]

    y_test = test_df[[value_col]]
    test_predictions = None
    future_forecast = None

    # --- Model Specific Logic ---

    if model_name == 'XGBoost':
        X_train, y_train = _create_features(train_df.copy(), value_col)
        X_test, _ = _create_features(test_df.copy(), value_col)

        reg = xgb.XGBRegressor(**params)
        reg.fit(X_train, y_train,
                eval_set=[(X_train, y_train), (X_test, y_test[value_col])],
                verbose=False)

        test_predictions = reg.predict(X_test)
        test_predictions = pd.DataFrame(test_predictions, index=test_df.index, columns=['prediction'])

        # Retrain on full data for future forecast
        X_full, y_full = _create_features(df.copy(), value_col)
        reg.fit(X_full, y_full, verbose=False)

        future_dates = pd.date_range(start=df.index[-1], periods=forecast_horizon + 1, freq=df.index.freq)[1:]
        future_df = pd.DataFrame(index=future_dates)
        future_df[value_col] = 0 # Placeholder
        X_future, _ = _create_features(future_df, value_col)

        future_preds = reg.predict(X_future)
        future_forecast = pd.DataFrame(future_preds, index=future_dates, columns=['prediction'])

    elif model_name == 'Prophet':
        prophet_train_df = train_df.reset_index().rename(columns={df.index.name: 'ds', value_col: 'y'})

        model = Prophet(**params)
        model.fit(prophet_train_df)

        future_test = model.make_future_dataframe(periods=len(test_df), freq=df.index.freq)
        test_forecast = model.predict(future_test)

        test_predictions = test_forecast.iloc[-len(test_df):][['ds', 'yhat']].set_index('ds')
        test_predictions.rename(columns={'yhat': 'prediction'}, inplace=True)

        # Retrain on full data
        full_prophet_df = df.reset_index().rename(columns={df.index.name: 'ds', value_col: 'y'})
        model.fit(full_prophet_df)

        future_dates = model.make_future_dataframe(periods=forecast_horizon, freq=df.index.freq)
        forecast = model.predict(future_dates)
        future_forecast = forecast.iloc[-forecast_horizon:][['ds', 'yhat']].set_index('ds')
        future_forecast.rename(columns={'yhat': 'prediction'}, inplace=True)

    elif model_name == 'ARIMA':
        order = (params['p'], params['d'], params['q'])
        model = ARIMA(train_df[value_col], order=order)
        results = model.fit()

        test_predictions = results.get_forecast(steps=len(test_df)).predicted_mean
        test_predictions = pd.DataFrame(test_predictions, index=test_df.index, columns=['prediction'])

        # Retrain on full data
        full_model = ARIMA(df[value_col], order=order)
        full_results = full_model.fit()

        future_preds = full_results.get_forecast(steps=forecast_horizon).predicted_mean
        future_forecast = pd.DataFrame(future_preds, columns=['prediction'])

    else:
        raise ValueError(f"Unknown model: {model_name}")

    # Calculate metrics
    rmse, mape = _calculate_metrics(y_test[value_col], test_predictions['prediction'])

    results_dict = {
        'historical_data': df[[value_col]],
        'test_predictions': test_predictions,
        'future_forecast': future_forecast,
        'rmse': rmse,
        'mape': mape * 100 # Return as percentage
    }

    return results_dict
