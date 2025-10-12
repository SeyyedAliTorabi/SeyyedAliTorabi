import os
import tensorflow as tf
from .config import MODEL_CONFIG
from . import metrics

def load_base_model(model_name: str):
    """
    Loads a pretrained base model.
    """
    if model_name not in MODEL_CONFIG:
        return None

    model_path = MODEL_CONFIG[model_name]
    # This is still a placeholder, as the actual model files don't exist.
    # In a real application, you would load the model from the files.
    # For example:
    # with open(os.path.join(model_path, 'config.json'), 'r') as f:
    #     model_config = json.load(f)
    # model = tf.keras.models.model_from_json(model_config)
    # model.load_weights(os.path.join(model_path, 'model.weights.h5'))

    # Using a simple sequential model as a placeholder
    model = tf.keras.models.Sequential([
        tf.keras.layers.Dense(128, activation='relu', input_shape=(10,)),
        tf.keras.layers.Dense(64, activation='relu'),
        tf.keras.layers.Dense(1)
    ])
    return model

def fine_tune_and_save_model(model, user_id: int, model_name: str, processed_data):
    """
    Fine-tunes the model on the user's data, calculates metrics, and saves the model.
    Returns the save path and the calculated metrics.
    """
    # Freeze the base layers
    for layer in model.layers[:-1]: # Freeze all but the last layer
        layer.trainable = False

    # Compile the model
    model.compile(optimizer='adam', loss='mse')

    # In a real scenario, you would prepare your data (X_train, y_train, X_val, y_val)
    import numpy as np
    X_train = np.random.rand(100, 10)
    y_train = np.random.rand(100, 1)
    X_val = np.random.rand(20, 10)
    y_val = np.random.rand(20, 1)

    # Fine-tune the model
    model.fit(X_train, y_train, epochs=10, batch_size=32, validation_data=(X_val, y_val), verbose=0)

    # Make predictions and calculate metrics
    y_pred = model.predict(X_val)
    eval_metrics = metrics.calculate_metrics(y_val, y_pred)

    # Save the fine-tuned model
    save_path_dir = f"fine_tuned_models/{user_id}/{model_name}/"
    os.makedirs(save_path_dir, exist_ok=True)
    model_save_path = os.path.join(save_path_dir, "model_finetuned.h5")
    model.save(model_save_path)

    return model_save_path, eval_metrics
