from pydantic import BaseModel
from datetime import datetime

class UserCreate(BaseModel):
    first_name: str
    last_name: str
    city: str
    water_organization: str
    national_id: str
    password: str

class User(BaseModel):
    id: int
    first_name: str
    last_name: str
    city: str
    water_organization: str
    national_id: str

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    national_id: str | None = None

class TrainingResultBase(BaseModel):
    model_name: str
    mae: float
    mape: float
    rmse: float
    mse: float
    fine_tuned_model_path: str
    forecast_horizon: int
    confidence_bounds: float
    training_chart_path: str
    forecast_chart_path: str

class TrainingResultCreate(TrainingResultBase):
    pass

class TrainingResult(TrainingResultBase):
    id: int
    user_id: int
    training_datetime: datetime

    class Config:
        orm_mode = True
