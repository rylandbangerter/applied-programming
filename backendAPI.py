from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional

# Import the helper functions and potentially the global model variable from useAnImportedModel
# Import _model to check if it's loaded
from useAnImportedModel import load_xgb_model, predict_with_loaded_model, get_expected_features_count, _model

MODEL_PATH = "predict_BA.json"

# Init fast api
app = FastAPI(
    title="Baseball prediction endpoint",
    description="A baseball predicting model endpoint"
)

# --- Define Pydantic Models ---
# 1. Input model: What the client sends to your API


class PredictionInput(BaseModel):
    # This list will hold the features your model expects
    # You might want to define specific named fields if your model has clear, named features
    features: List[float] = Field(
        ...,  # Indicates this field is required
        description="A list of numerical features for the baseball prediction model."
    )

    class Config:
        json_schema_extra = {
            "example": {
                # Adjust example features based on your model
                "names": [],
                "features": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
            }
        }

# 2. Output model: What your API sends back to the client


class PredictionOutput(BaseModel):
    prediction: float
    message: str = "Prediction successful"
    # Optional, if your model outputs confidence
    confidence: Optional[float] = None

    class Config:
        json_schema_extra = {
            "example": {
                "prediction": 0.75,
                "message": "Prediction successful"
            }
        }

# --- Load the model when the application starts ---
# This is crucial for performance. The model is loaded only once.


@app.on_event("startup")
async def startup_event():
    """Load the ML model when the FastAPI application starts."""
    try:
        load_xgb_model(MODEL_PATH)
        expected_count = get_expected_features_count()
        if _model:
            print(f"ML model '{MODEL_PATH}' loaded successfully.")
            if expected_count is not None:
                print(f"Model expects {expected_count} features.")
            else:
                print("Could not determine expected number of features from the model.")
        else:
            raise RuntimeError("Model loading failed, _model is still None.")
    except Exception as e:
        print(f"FATAL ERROR: Could not load the ML model at startup: {e}")
        # In a production environment, you might want to stop the server here
        # or have a health check that fails. For development, just log.


# --- Root endpoint (optional, for health check or info) ---
@app.get("/")
async def read_root():
    return {"message": "Welcome to the Baseball Prediction API! Use /predict to get predictions."}


# --- Prediction Endpoint ---
@app.post("/predict", response_model=PredictionOutput)  # Corrected syntax
# input_data will be an instance of PredictionInput
async def predict(input_data: PredictionInput):
    if _model is None:
        raise HTTPException(
            status_code=503, detail="Prediction model is not loaded. Please check server logs.")

    expected_features_count = get_expected_features_count()
    if expected_features_count is not None and len(input_data.features) != expected_features_count:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid number of features. Expected {
                expected_features_count}, but received {len(input_data.features)}."
        )

    try:
        # Call the helper function with the features from the request
        prediction_result = predict_with_loaded_model(input_data.features)
        return PredictionOutput(prediction=prediction_result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Input data error: {e}")
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {e}")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred during prediction: {e}")
