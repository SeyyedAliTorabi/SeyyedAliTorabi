import pandas as pd

def load_and_validate(filepath):
    """
    Loads a CSV or Excel file and performs initial validation.

    Args:
        filepath (str): The path to the data file.

    Returns:
        pd.DataFrame: The loaded data as a pandas DataFrame.
    """
    if not filepath:
        raise ValueError("No file path provided.")

    if filepath.endswith('.csv'):
        df = pd.read_csv(filepath)
    elif filepath.endswith(('.xls', '.xlsx')):
        df = pd.read_excel(filepath)
    else:
        raise ValueError("Invalid file format. Please select a CSV or Excel file.")

    if df.empty:
        raise ValueError("The selected file is empty.")

    if len(df.columns) < 2:
        raise ValueError("The data must have at least two columns (for timestamp and value).")

    return df

def preprocess(df, timestamp_col, value_col):
    """
    Preprocesses the DataFrame by setting the index and handling missing values.

    Args:
        df (pd.DataFrame): The input DataFrame.
        timestamp_col (str): The name of the timestamp column.
        value_col (str): The name of the value column to be forecasted.

    Returns:
        tuple: A tuple containing:
            - pd.DataFrame: The preprocessed DataFrame.
            - str: A report describing the preprocessing steps.
    """
    if timestamp_col not in df.columns or value_col not in df.columns:
        raise ValueError("Timestamp or value column not found in the DataFrame.")

    # Work on a copy to avoid side effects
    processed_df = df[[timestamp_col, value_col]].copy()

    # Convert to datetime and set as index
    processed_df[timestamp_col] = pd.to_datetime(processed_df[timestamp_col])
    processed_df.set_index(timestamp_col, inplace=True)
    processed_df.sort_index(inplace=True)

    # Ensure the value column is numeric
    processed_df[value_col] = pd.to_numeric(processed_df[value_col], errors='coerce')

    # Handle NaNs
    initial_nan_count = processed_df[value_col].isna().sum()

    # Interpolate small gaps (e.g., up to 3 consecutive NaNs)
    processed_df[value_col] = processed_df[value_col].interpolate(method='linear', limit=3, limit_direction='both')

    nans_after_interp = processed_df[value_col].isna().sum()
    interpolated_count = initial_nan_count - nans_after_interp

    # Drop any remaining NaNs (from larger gaps or ends)
    processed_df.dropna(inplace=True)

    dropped_count = nans_after_interp

    report = (f"Filled {interpolated_count} NaN values using linear interpolation. "
              f"Removed {dropped_count} NaN values (in large gaps or at ends).")

    return processed_df, report
