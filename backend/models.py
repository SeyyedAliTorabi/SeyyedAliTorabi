from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    city = Column(String)
    water_organization = Column(String)
    national_id = Column(String, unique=True, index=True)
    hashed_password = Column(String)

    results = relationship("TrainingResult", back_populates="user")

    def __repr__(self):
        return f"<User(national_id='{self.national_id}')>"

class TrainingResult(Base):
    __tablename__ = "training_results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    model_name = Column(String)
    training_datetime = Column(DateTime, default=datetime.datetime.utcnow)
    mae = Column(Float)
    mape = Column(Float)
    rmse = Column(Float)
    mse = Column(Float)
    fine_tuned_model_path = Column(String)
    forecast_horizon = Column(Integer)
    confidence_bounds = Column(Float)
    training_chart_path = Column(String)
    forecast_chart_path = Column(String)

    user = relationship("User", back_populates="results")
