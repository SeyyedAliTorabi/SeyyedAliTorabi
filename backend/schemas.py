from pydantic import BaseModel
from typing import List, Optional
import datetime

class TrainingResultBase(BaseModel):
    model_name: str
    mae: float
    mape: float
    rmse: float
    mse: float
    model_path: str
    chart_file_paths: str
    forecast_intervals: str
    confidence_bounds: str

class TrainingResultCreate(TrainingResultBase):
    pass

class TrainingResult(TrainingResultBase):
    id: int
    user_id: int
    timestamp: datetime.datetime

    class Config:
        orm_mode = True

class UserBase(BaseModel):
    first_name: str
    last_name: str
    city: str
    organization: str
    national_id: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    results: List[TrainingResult] = []

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    national_id: Optional[str] = None
