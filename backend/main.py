from fastapi import Depends, FastAPI, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
import uvicorn
from datetime import timedelta
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt

from . import models, schemas, security, database, processing, training, visualization

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Dependency
def get_db():
    db = database.SessionLocal()
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
    except jwt.PyJWTError:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.national_id == token_data.national_id).first()
    if user is None:
        raise credentials_exception
    return user

@app.post("/register/", response_model=schemas.User)
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

@app.post("/login/", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
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

@app.post("/uploadfile/")
async def create_upload_file(file: UploadF ile = File(...), current_user: models.User = Depends(get_current_user)):
    df = processing.process_uploaded_file(file, current_user.id)
    return {"filename": file.filename, "dataframe_shape": df.shape}

@app.post("/finetune/{model_name}")
async def finetune_model(model_name: str, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    model_path, metrics, y_true, y_pred = training.fine_tune_and_evaluate(model_name, current_user.id)

    # Create a preliminary result to get an ID for the plots
    db_result = models.TrainingResult(user_id=current_user.id, model_name=model_name)
    db.add(db_result)
    db.commit()
    db.refresh(db_result)

    # Generate plots
    actual_vs_pred_path = visualization.plot_actual_vs_predicted(current_user.id, db_result.id, y_true, y_pred)
    forecast_path, forecast_intervals, confidence_bounds = visualization.plot_forecast_with_confidence(current_user.id, db_result.id, y_pred) # Using y_pred as dummy forecast

    # Update the result with all the data
    db_result.mae = metrics["mae"]
    db_result.mape = metrics["mape"]
    db_result.rmse = metrics["rmse"]
    db_result.mse = metrics["mse"]
    db_result.model_path = model_path
    db_result.chart_file_paths = f"{actual_vs_pred_path},{forecast_path}"
    db_result.forecast_intervals = forecast_intervals
    db_result.confidence_bounds = confidence_bounds

    db.commit()
    db.refresh(db_result)

    return {"message": f"Model {model_name} fine-tuned successfully.", "results": db_result}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
