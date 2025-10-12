import pandas as pd
import jdatetime

def to_daily_aggregation(df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    """
    Resamples the dataframe to a daily frequency, taking the mean of the value column.
    """
    df_daily = df.set_index('timestamp').resample('24H').mean()
    # Fill missing days with the average daily consumption
    mean_consumption = df_daily[value_col].mean()
    df_daily[value_col] = df_daily[value_col].fillna(mean_consumption)
    return df_daily.reset_index()

def generate_jalali_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generates Jalali calendar features for the given dataframe.
    """
    df['jalali_date'] = df['timestamp'].apply(lambda d: jdatetime.date.fromgregorian(date=d))

    # A more comprehensive list would be needed for a production system
    national_holidays = [jdatetime.date(year, 1, 1) for year in range(1390, 1411)] # Nowruz
    religious_holidays = [jdatetime.date(year, 2, 15) for year in range(1390, 1411)] # Example holiday

    df['is_friday'] = df['jalali_date'].apply(lambda d: d.weekday() == 6)
    df['is_national_holiday'] = df['jalali_date'].isin(national_holidays)
    df['is_religious_holiday'] = df['jalali_date'].isin(religious_holidays)

    df['day_of_week'] = df['jalali_date'].apply(lambda d: d.weekday())
    df['month'] = df['jalali_date'].apply(lambda d: d.month)

    return df
