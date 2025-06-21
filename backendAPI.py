from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd
import numpy as np
import os
import joblib
from typing import Dict, List, Any
import logging

# Import your utility functions
from .model_utils import (
    fetch_and_clean_player_data,
    prepare_features_and_targets,
    add_user_input_opponent,
    get_opponent_specific_lagged_features,  # Use this for prediction input
    train_model,
    save_multioutput_model,
    load_multioutput_model
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Baseball Player Stat Predictor",
    description="API for predicting player statistics using an XGBoost model.",
    version="1.0.0"
)

# --- Global variables for the model and feature columns ---
# We'll load the model and feature columns once when the app starts
# Store models per player/stat combination if needed
model_storage: Dict[str, Any] = {}
# To store the exact feature columns used during training
all_feature_columns: List[str] = []
# Default stat, can be overridden by training if multiple
selected_stat_global: str = "TB"
# or if you adapt the API to predict multiple stats


# --- Pydantic models for request and response ---

class PredictionRequest(BaseModel):
    player_name: str
    selected_stat: str  # e.g., "TB", "H", "HR"
    opponent: str      # e.g., "SEA", "NYY"


class PredictionResponse(BaseModel):
    player_name: str
    selected_stat: str
    opponent: str
    predicted_value: float
    message: str = "Prediction successful"
    # For debugging, can be removed in production
    debug_info: Dict[str, Any] = {}


# --- FastAPI Lifespan Events (for model loading/training) ---
@app.on_event("startup")
async def startup_event():
    logger.info("Application startup: Initializing model...")
    # This is where you would typically load your *pre-trained* model.
    # For this example, we'll also run the full training process for demonstration.
    # In a real production environment, you'd train offline and only load here.

    global all_feature_columns
    global selected_stat_global

    player_name_for_training = "Jose_Altuve"
    selected_stat_global = "TB"  # Or any other default stat you want to train on startup
    # Just for training context, not used for actual prediction logic here
    opponent_for_training = "SEA"

    model_path = f"models/{player_name_for_training}_{
        selected_stat_global}_model.joblib"

    if os.path.exists(model_path):
        try:
            # Load the pre-trained model
            loaded_model = load_multioutput_model(model_path)
            model_storage[f"{player_name_for_training}_{
                selected_stat_global}"] = loaded_model

            # Need to also load/store the feature columns that this model was trained on
            # This is crucial for consistent prediction input
            # In a production setup, you'd save these feature names alongside the model.
            # For now, let's re-run the data prep to get them, or manually define them if fixed.
            # A better way: save a list of feature columns with your model.

            # Temporary: re-run data prep to get feature columns
            df_temp = fetch_and_clean_player_data(
                player_name_for_training, selected_stat_global)
            features_temp, _, _ = prepare_features_and_targets(
                df_temp, selected_stat_global)
            all_feature_columns = features_temp.columns.tolist()

            logger.info(f"Loaded existing model for {
                        player_name_for_training} ({selected_stat_global}).")

        except Exception as e:
            logger.error(f"Error loading existing model: {
                         e}. Retraining instead.")
            # Fallback to training if loading fails
            df = fetch_and_clean_player_data(
                player_name_for_training, selected_stat_global)
            features, targets, _ = prepare_features_and_targets(
                df, selected_stat_global)

            # Ensure features for opponent-specific lags are added *before* training if needed
            # For the training process, `add_opponent_lagged_stats` needs to be used to enrich `features`
            # The current `add_opponent_lagged_stats` in model_utils.py doesn't modify features for training well.
            # If you want opponent-specific lagged features to be *trained on*, you need to add them to `features` DataFrame.
            # Example: features = add_opponent_lagged_stats(df.copy(), selected_stat_global, opponent_for_training)
            # This is complex because each row in the training data has a *different* opponent.
            # You would need to apply `get_opponent_specific_lagged_features` for *each historical game* based on its opponent.

            trained_model, _ = train_model(features, targets)
            save_multioutput_model(trained_model, model_path)
            model_storage[f"{player_name_for_training}_{
                selected_stat_global}"] = trained_model
            all_feature_columns = features.columns.tolist()
            logger.info(f"Trained and saved new model for {
                        player_name_for_training} ({selected_stat_global}).")

    else:
        logger.info(f"No existing model found for {player_name_for_training} ({
                    selected_stat_global}). Training a new one...")
        try:
            df = fetch_and_clean_player_data(
                player_name_for_training, selected_stat_global)
            features, targets, _ = prepare_features_and_targets(
                df, selected_stat_global)
            # As noted above, if you want opponent-specific lagged features *trained into the model*,
            # you need to incorporate them into the `features` DataFrame during this training step.
            # This would likely involve a loop over the historical data to calculate `get_opponent_specific_lagged_features`
            # for each historical game based on its opponent and then adding those columns.
            # For simplicity, if `Opp_SEA` etc. from `pd.get_dummies` is sufficient, then no change needed here.

            trained_model, _ = train_model(features, targets)
            save_multioutput_model(trained_model, model_path)
            model_storage[f"{player_name_for_training}_{
                selected_stat_global}"] = trained_model
            all_feature_columns = features.columns.tolist()
            logger.info(f"Trained and saved new model for {
                        player_name_for_training} ({selected_stat_global}).")
        except Exception as e:
            logger.error(f"Failed to train model at startup: {e}")
            raise RuntimeError(f"Failed to initialize model at startup: {e}")


@app.get("/")
async def root():
    return {"message": "Baseball Player Stat Prediction API is running!"}


@app.post("/predict", response_model=PredictionResponse)
async def predict_stat(request: PredictionRequest):
    player_name = request.player_name
    selected_stat = request.selected_stat
    opponent = request.opponent

    # Check if the model for this player/stat is loaded
    model_key = f"{player_name}_{selected_stat}"
    if model_key not in model_storage:
        raise HTTPException(status_code=404, detail=f"Model for {player_name} and {
                            selected_stat} not found. Please ensure it's trained and loaded.")

    model = model_storage[model_key]

    try:
        # 1. Fetch player's historical data
        # Note: This fetches *all* data for the player. We need the raw 'df' for opponent-specific lags.
        historical_df = fetch_and_clean_player_data(player_name, selected_stat)

        # 2. Prepare features for the *new* prediction input
        # We need to simulate a new game, so we use the structure of the last historical game.
        # However, we remove the actual 'selected_stat' value as it's what we want to predict.

        # Take the last row of the cleaned historical_df as a base for prediction input
        # It already has `_lag1`, `_lag3`, `_rolling3` features computed from historical data.

        # Prepare features (one-hot encoding etc.) for all historical data
        # This gives us the complete set of feature columns that the model expects
        features_for_prep, _, _ = prepare_features_and_targets(
            historical_df, selected_stat)

        # Get the latest game's features as a template for the prediction
        latest_game_features_template = features_for_prep.iloc[[-1]].copy()

        # Add user-specified opponent to the prediction input
        # This function modifies the opponent columns for the *single prediction row*
        prediction_input_df = add_user_input_opponent(
            latest_game_features_template, opponent)

        # Add opponent-specific lagged features to the prediction input
        # We need to calculate these based on the `historical_df`
        opponent_lag_feats = get_opponent_specific_lagged_features(
            historical_df, selected_stat, opponent)
        for col, val in opponent_lag_feats.items():
            # Add these new columns to the prediction_input_df
            prediction_input_df[col] = val

        # Ensure prediction_input_df has all and only the columns that the model was trained on, in the correct order.
        # This is critical! If feature columns mismatch, prediction will fail or be inaccurate.
        # First, ensure all_feature_columns is populated.
        if not all_feature_columns:
            # Fallback if startup didn't populate it (e.g., if you skipped training/loading)
            # This should ideally be populated during startup and model loading
            df_temp = fetch_and_clean_player_data(player_name, selected_stat)
            features_temp, _, _ = prepare_features_and_targets(
                df_temp, selected_stat)
            all_feature_columns = features_temp.columns.tolist()

        # Align columns of the input with the training columns
        missing_cols = set(all_feature_columns) - \
            set(prediction_input_df.columns)
        for c in missing_cols:
            prediction_input_df[c] = 0.0  # Or appropriate default value

        extra_cols = set(prediction_input_df.columns) - \
            set(all_feature_columns)
        prediction_input_df = prediction_input_df.drop(
            columns=list(extra_cols))

        prediction_input_df = prediction_input_df[all_feature_columns]

        logger.info(f"Prediction input shape: {prediction_input_df.shape}")
        # logger.info(f"Prediction input sample:\n{prediction_input_df.head().T}") # Too verbose for production logs

        # 3. Make prediction
        prediction_array = model.predict(prediction_input_df)[0]
        # Assuming MultiOutputRegressor always returns an array of predictions
        predicted_value = prediction_array[0]

        return PredictionResponse(
            player_name=player_name,
            selected_stat=selected_stat,
            opponent=opponent,
            predicted_value=round(float(predicted_value), 3),
            debug_info={
                "input_features_count": len(prediction_input_df.columns),
                "model_feature_count": len(all_feature_columns),
                # "input_features_sample": prediction_input_df.iloc[0].to_dict() # Only for deep debugging
            }
        )

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except ConnectionError as ce:
        raise HTTPException(
            status_code=500, detail=f"Firebase connection error: {str(ce)}")
    except Exception as e:
        logger.exception("An error occurred during prediction:")
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {e}")
