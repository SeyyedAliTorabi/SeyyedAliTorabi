from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, mean_squared_error
import numpy as np

def calculate_metrics(y_true, y_pred):
    """
    Calculates a dictionary of evaluation metrics.
    """
    metrics = {
        "mae": mean_absolute_error(y_true, y_pred),
        "mape": mean_absolute_percentage_error(y_true, y_pred),
        "rmse": np.sqrt(mean_squared_error(y_true, y_pred)),
        "mse": mean_squared_error(y_true, y_pred)
    }
    return metrics
