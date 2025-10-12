from .config import MODEL_CONFIG
import os
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
import numpy as np
import time

def load_model(model_name: str):
    if model_name not in MODEL_CONFIG:
        raise ValueError(f"Model {model_name} not found in MODEL_CONFIG")

    model_path = MODEL_CONFIG[model_name]

    required_files = [
        "model.weights.h5",
        "config.json",
        "metadata.json",
        "preprocessor.pkl",
        "training_log.json"
    ]

    for file in required_files:
        filepath = os.path.join("backend", model_path, file)
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Required file not found: {filepath}")

    # In a real application, you would load the model here
    print(f"Loading model: {model_name} from {model_path}")

    return {"model_name": model_name, "status": "loaded_successfully"}

def fine_tune_and_evaluate(model_name: str, user_id: int):
    # --- IMPLEMENTATION NOTE ---
    # The following is a PLACEHOLDER for the actual model fine-tuning process.
    # In a real-world application, this function would:
    #   1. Load the weights of the specified pre-trained model (e.g., using TensorFlow/Keras or PyTorch).
    #   2. Use the user's data (`df`) to perform transfer learning or fine-tuning on the model weights.
    #      This would be a CPU-intensive operation.
    #   3. Implement early stopping based on a validation set to prevent overfitting.
    #   4. Save the newly trained model weights to the specified `finetuned_model_path`.
    #   5. Use the fine-tuned model to generate predictions on a test set to produce `y_pred`.
    # -------------------------

    # 1. Load the base model
    model = load_model(model_name)

    # 2. Load the user's preprocessed data
    processed_file_path = f"backend/user_data/{user_id}/data_processed.parquet"
    try:
        df = pd.read_parquet(processed_file_path)
    except FileNotFoundError:
        raise ValueError("Processed data not found. Please upload a file first.")

    # 3. Simulate CPU-only fine-tuning
    print(f"Starting fine-tuning for model {model_name} for user {user_id}...")
    # Freeze hyperparameters, train only model weights, use early stopping
    time.sleep(5) # Simulate training time
    print("Fine-tuning complete.")

    # 4. Save the fine-tuned model
    finetuned_model_dir = f"backend/fine_tuned_models/{user_id}/{model_name}/"
    os.makedirs(finetuned_model_dir, exist_ok=True)
    finetuned_model_path = os.path.join(finetuned_model_dir, "model_finetuned.h5")
    with open(finetuned_model_path, "w") as f:
        f.write("This is a dummy fine-tuned model.")

    # 5. Simulate predictions and evaluate
    # In a real scenario, you'd use the fine-tuned model to predict on a validation set
    y_true = df['consumption']
    # Generate dummy predictions for evaluation
    np.random.seed(42)
    y_pred = y_true * (1 + np.random.normal(0, 0.1, len(y_true)))

    mae = mean_absolute_error(y_true, y_pred)
    mse = mean_squared_error(y_true, y_pred)
    rmse = np.sqrt(mse)
    mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100

    metrics = {
        "mae": mae,
        "mape": mape,
        "rmse": rmse,
        "mse": mse
    }

    print(f"Evaluation metrics: {metrics}")

    return finetuned_model_path, metrics, y_true, y_pred
