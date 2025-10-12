from fastapi import Depends, FastAPI, HTTPException, status, File, UploadFile
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import pandas as pd
from jose import JWTError, jwt
from pydantic import BaseModel
from typing import List
from datetime import timedelta
from . import models, schemas, security, processing, training
from .database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        national_id: str = payload.get("sub")
        if national_id is None:
            raise credentials_exception
        token_data = schemas.TokenData(national_id=national_id)
    except JWTError:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.national_id == token_data.national_id).first()
    if user is None:
        raise credentials_exception
    return user

@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.national_id == user.national_id).first()
    if db_user:
        raise HTTPException(status_code=400, detail="National ID already registered")
    hashed_password = security.get_password_hash(user.password)
    db_user = models.User(**user.dict(exclude={"password"}), hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.national_id == form_data.username).first()
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect national ID or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.national_id}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me/", response_model=schemas.User)
async def read_users_me(current_user: schemas.User = Depends(get_current_user)):
    return current_user

@app.post("/uploadfile/")
class FineTuneRequest(BaseModel):
    processed_data: List[dict]

async def create_upload_file(file: UploadFile = File(...), value_col: str = 'water_consumption'):
    if file.content_type not in ["text/csv", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
        raise HTTPException(status_code=400, detail="Invalid file type")

    try:
        if file.content_type == "text/csv":
            df = pd.read_csv(file.file)
        else:
            df = pd.read_excel(file.file)

        # Basic validation and processing
        if "timestamp" not in df.columns or value_col not in df.columns:
            raise HTTPException(status_code=400, detail=f"Missing 'timestamp' or '{value_col}' column")

        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df = df.drop_duplicates().sort_values(by="timestamp")

        # Daily aggregation and feature engineering
        df_daily = processing.to_daily_aggregation(df, value_col)
        df_processed = processing.generate_jalali_features(df_daily)

        return {"filename": file.filename, "processed_data": df_processed.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {e}")

@app.post("/finetune/{model_name}", response_model=schemas.TrainingResult)
async def finetune_model(
    model_name: str,
    request: FineTuneRequest,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user)
):
    model = training.load_base_model(model_name)
    if model is None:
        raise HTTPException(status_code=404, detail="Model not found")

    try:
        saved_model_path, eval_metrics = training.fine_tune_and_save_model(
            model, current_user.id, model_name, request.processed_data
        )

        training_result_data = schemas.TrainingResultCreate(
            model_name=model_name,
            mae=eval_metrics["mae"],
            mape=eval_metrics["mape"],
            rmse=eval_metrics["rmse"],
            mse=eval_metrics["mse"],
            fine_tuned_model_path=saved_model_path,
        )

        db_training_result = models.TrainingResult(**training_result_data.dict(), user_id=current_user.id)
        db.add(db_training_result)
        db.commit()
        db.refresh(db_training_result)

        return db_training_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during fine-tuning: {e}")
