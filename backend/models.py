from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, index=True)
    last_name = Column(String, index=True)
    city = Column(String)
    organization = Column(String)
    national_id = Column(String, unique=True, index=True)
    hashed_password = Column(String)

    results = relationship("TrainingResult", back_populates="owner")

class TrainingResult(Base):
    __tablename__ = "training_results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    model_name = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    mae = Column(Float)
    mape = Column(Float)
    rmse = Column(Float)
    mse = Column(Float)
    model_path = Column(String)
    chart_file_paths = Column(String)
    forecast_intervals = Column(String)
    confidence_bounds = Column(String)

    owner = relationship("User", back_populates="results")
