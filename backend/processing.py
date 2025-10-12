import pandas as pd
import jdatetime
import json
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from fastapi import UploadFile, HTTPException
import io
import os

def load_holidays(holiday_file: str = "backend/holidays.json"):
    with open(holiday_file, "r") as f:
        return json.load(f)

HOLIDAYS = load_holidays()

def process_uploaded_file(file: UploadFile, user_id: int):
    if not (file.filename.endswith(".csv") or file.filename.endswith(".xlsx")):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload a CSV or Excel file.")

    try:
        if file.filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(file.file.read()))
        else:
            df = pd.read_excel(io.BytesIO(file.file.read()))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {e}")

    # Basic validation
    if len(df.columns) != 2:
        raise HTTPException(status_code=400, detail="Invalid file structure. Expected 2 columns: [Persian date YYYY/MM/DD, daily consumption in cubic meters]")

    df.columns = ["date", "consumption"]

    # Data cleaning
    df.dropna(inplace=True)
    df.drop_duplicates(inplace=True)

    # Date conversion and feature engineering
    df['gregorian_date'] = df['date'].apply(lambda x: jdatetime.datetime.strptime(x, '%Y/%m/%d').togregorian().date())
    df.set_index(pd.to_datetime(df['gregorian_date']), inplace=True)
    df.sort_index(inplace=True)

    df['is_national_holiday'] = df['date'].apply(is_national_holiday)
    df['is_religious_holiday'] = df['date'].apply(is_religious_holiday)
    df['is_friday'] = df.index.dayofweek == 4  # Friday is the 4th day of the week in jdatetime

    # Resampling
    df = df.resample('24H').mean()
    df['consumption'].interpolate(method='linear', inplace=True)

    # Feature engineering (time components)
    df['day_of_week'] = df.index.dayofweek
    df['month'] = df.index.month

    # Scaling
    scaler = StandardScaler()
    df['consumption_scaled'] = scaler.fit_transform(df[['consumption']])

    # FIFO cleanup (if more than 100,000 records)
    if len(df) > 100000:
        df = df.iloc[-100000:]

    # Save to a user-specific directory
    user_data_dir = f"backend/user_data/{user_id}/"
    os.makedirs(user_data_dir, exist_ok=True)
    processed_file_path = os.path.join(user_data_dir, "data_processed.parquet")
    df.to_parquet(processed_file_path)

    return df

def is_national_holiday(persian_date: str):
    year = persian_date.split("/")[0]
    return persian_date in HOLIDAYS.get(year, {}).get("national", [])

def is_religious_holiday(persian_date: str):
    year = persian_date.split("/")[0]
    return persian_date in HOLIDAYS.get(year, {}).get("religious", [])
