import joblib
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.multioutput import MultiOutputRegressor
import os
import re

# Firebase Setup - Initialize only once
# This is crucial for FastAPI. We initialize it outside functions
# so it's ready when the FastAPI app starts.
try:
    firebase_key_path = os.environ.get("FIREBASE_KEY_PATH")
    if not firebase_key_path:
        # Fallback for local development if .env is used directly
        from dotenv import load_dotenv
        load_dotenv()
        firebase_key_path = os.environ.get("FIREBASE_KEY_PATH")
        if not firebase_key_path:
            raise ValueError(
                "No Firebase key path found. Please set FIREBASE_KEY_PATH in your environment or .env file.")

    # Check if app is already initialized to prevent re-initialization errors in development/testing
    if not firebase_admin._apps:
        cred = credentials.Certificate(firebase_key_path)
        firebase_admin.initialize_app(cred)
    db = firestore.client()
except Exception as e:
    print(f"Error initializing Firebase: {e}")
    db = None  # Set db to None if initialization fails


# === Lagged Features ===
def add_lagged_features(df, stats, lags=[1, 3], lag_weights={1: 1.2, 3: 1.1}, rolling_weight=1.3):
    for stat in stats:
        for lag in lags:
            column_name = f'{stat}_lag{lag}'
            df[column_name] = df[stat].shift(lag)
            df[column_name] *= lag_weights.get(lag, 1)

        rolling_name = f'{stat}_rolling3'
        df[rolling_name] = df[stat].rolling(3).mean().shift(1)
        df[rolling_name] *= rolling_weight
    return df

# === Load and Clean Player Data ===


def fetch_and_clean_player_data(player_name: str, selected_stat: str):
    if db is None:
        raise ConnectionError("Firebase not initialized. Cannot fetch data.")

    docs = db.collection("gameStats").stream()
    cleaned_data = []

    for doc in docs:
        doc_id = doc.id
        if not doc_id.startswith(player_name):
            continue

        raw = doc.to_dict()
        cleaned = {}

        for key, val in raw.items():
            val = str(val).strip()
            if re.match(r'^-?\d+\.?\d*%$', val):
                cleaned[key] = float(val.replace('%', '')) / 100
            elif re.match(r'^-?\d+\.?\d*$', val):
                cleaned[key] = float(val)
            else:
                cleaned[key] = val

        cleaned_data.append(cleaned)

    if not cleaned_data:
        raise ValueError(f"No data found for player: {player_name}")

    df = pd.DataFrame(cleaned_data)
    df = df.fillna(0)

    pos_col = [col for col in df.columns if "Pos" in col]
    if pos_col:
        df.rename(columns={pos_col[0]: "Pos"}, inplace=True)
        df["Pos"] = df["Pos"].str.strip().replace(
            {'\r': '', '\n': ''}, regex=True)

    if "Opp" in df.columns:
        df["Opp"] = df["Opp"].str.strip().replace(
            {'\r': '', '\n': '', ' ': ''}, regex=True)
        df["Opp"].fillna("Unknown", inplace=True)

    numeric_cols = ['OBP', 'OPS', 'SLG', 'BA']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Only add lags for the stat we are predicting
    target_stats_for_lag = [selected_stat]
    df = add_lagged_features(df, target_stats_for_lag, lags=[1, 3])

    # Drop incomplete lagged rows
    df = df.dropna().reset_index(drop=True)

    print(f"Loaded {len(cleaned_data)} games for {player_name}")
    return df

# === Define Features and Targets ===


def prepare_features_and_targets(df: pd.DataFrame, selected_stat: str):
    target_stats = [selected_stat]

    drop_cols = ['Date', 'Result', 'Team', 'DFS(DK)', 'DFS(FD)', 'WPA', 'cWPA', 'aLI', 'acLI',
                 'RE24', 'Rk', 'Inngs', 'Pos', 'Gtm', 'Gcar', '@/H', 'BOP', 'IBB', 'HBP', 'SH', 'SF', 'CS']

    # Ensure we don't drop the selected_stat itself if it's not a target,
    # but for prediction, we often don't have the current game's target.
    # For training, it's a target. For prediction, it's what we want.
    # The current logic will drop it from features if it's in drop_cols, which is correct for features.

    features = df.drop(
        columns=[col for col in drop_cols if col in df.columns], errors='ignore')

    # Exclude the actual target column from features for the *training* process
    # If the selected_stat is in features and is meant to be a target, remove it from features.
    if selected_stat in features.columns and selected_stat in target_stats:
        features = features.drop(columns=[selected_stat])

    numeric = features.select_dtypes(include=['float64', 'int64'])
    categorical = features.select_dtypes(exclude=['float64', 'int64'])

    if not categorical.empty:
        categorical = pd.get_dummies(categorical, drop_first=True)

    features = categorical.join(numeric).fillna(0)

    targets = df[target_stats].apply(pd.to_numeric, errors='coerce').fillna(0)

    return features, targets, target_stats

# === Select Opponent ===


def add_user_input_opponent(features: pd.DataFrame, user_opponent: str):
    # This function is specifically for preparing the *single* row for prediction.
    # For training, the Opponent columns should be based on historical data.

    # Identify existing opponent columns from training data
    existing_opp_cols = [
        col for col in features.columns if col.startswith('Opp_')]

    # Create a new DataFrame for the prediction input
    # Take the last row as a template for features
    pred_input_df = features.iloc[[-1]].copy()

    # Reset all existing opponent columns to False for the prediction row
    for col in existing_opp_cols:
        pred_input_df[col] = False

    # Set the selected opponent column to True for the prediction row
    opp_col_to_set = f'Opp_{user_opponent}'
    if opp_col_to_set in pred_input_df.columns:
        pred_input_df[opp_col_to_set] = True
    else:
        # If the specific opponent was never seen in training, we need to add the column
        # and set it to True. All other Opp_ columns will be False.
        # This is important for consistency in features.
        pred_input_df[opp_col_to_set] = True
        print(f"Info: Added new opponent column '{
              opp_col_to_set}' for prediction.")

    # Ensure all original features.columns are present in pred_input_df
    # Add missing columns with 0, drop extra columns
    for col in features.columns:
        if col not in pred_input_df.columns:
            # Add missing features as 0 (or appropriate default)
            pred_input_df[col] = 0.0

    for col in pred_input_df.columns:
        if col not in features.columns:
            pred_input_df = pred_input_df.drop(columns=[col])

    # Ensure the order of columns is identical
    pred_input_df = pred_input_df[features.columns]

    return pred_input_df


# === Weighted Opponent Stat ===
def add_opponent_lagged_stats(df: pd.DataFrame, selected_stat: str, user_opponent: str):
    # This function needs to operate on the *full* dataframe before the final prediction row is isolated.
    # The opponent-specific lagged stats are features derived from the historical data
    # themselves, not just for the prediction input.

    # Create a temporary column to mark games against the specific opponent
    df['is_target_opponent'] = (df['Opp'] == user_opponent)

    # Calculate lagged stats for the selected_stat specifically against the user_opponent
    for lag in [1, 3, 5]:
        lagged_col_name = f'{selected_stat}_vs_{user_opponent}_lag{lag}'
        # Get the 'selected_stat' values only for games against the user_opponent
        # Shift these values, and then merge back to the original DataFrame
        df[lagged_col_name] = np.nan

        # This is a bit tricky. We want the lag from *previous games against this specific opponent*.
        # The current implementation in the original code is a bit ambiguous for general use.
        # A more robust way would be to group by player and opponent, and then apply shift.
        # For simplicity for FastAPI, let's assume this means the last N games *overall* against that opponent.

        # More robust way: Group by opponent and apply shift within each group
        # This would require more complex data structuring if your DB doesn't give opponent for all rows
        # For now, let's assume the current structure and how it was intended

        # Let's adjust the logic to make it clearer for the prediction context
        # We need the most recent stats of the player *against that specific opponent*

        # Filter for games against the specific opponent
        opp_games_df = df[df['Opp'] == user_opponent].copy()

        if not opp_games_df.empty:
            # Sort by date (assuming 'Date' is present and chronological)
            if 'Date' in opp_games_df.columns:
                opp_games_df = opp_games_df.sort_values(by='Date')

            for lag_val in [1, 3, 5]:
                lagged_stat = opp_games_df[selected_stat].shift(lag_val)
                # Apply this lagged stat only to the row that represents the *current* game against that opponent
                # This is more complex if the original df is not sorted by date overall.
                # For a single prediction, we need the last relevant values.

                # A simpler approach for the prediction input:
                # Find the player's last game against this opponent in the *historical* data.
                # Then use its 'selected_stat' value as the lag1 feature for the *prediction*.
                pass  # This function's output will be handled differently for live prediction

    # For the FastAPI prediction, we'll need to manually calculate these specific lagged features
    # for the single prediction row based on the historical data.
    # For the training data, this function might not add useful features directly.
    return df

# Simplified version of add_opponent_lagged_stats for *prediction input*


def get_opponent_specific_lagged_features(df: pd.DataFrame, selected_stat: str, user_opponent: str):
    # Filter games played against this opponent, sort by date (assuming 'Date' exists and is sortable)
    opp_games = df[df['Opp'] == user_opponent].sort_values(
        by='Date', ascending=False)

    lagged_features_for_prediction = {}
    for lag in [1, 3, 5]:
        col_name = f'{selected_stat}_vs_{user_opponent}_lag{lag}'
        if len(opp_games) >= lag:
            # Get the stat from the (lag)-th most recent game against this opponent
            lagged_features_for_prediction[col_name] = opp_games.iloc[lag - 1][selected_stat]
        else:
            # Or some other sensible default if not enough history
            lagged_features_for_prediction[col_name] = 0.0
    return lagged_features_for_prediction


# === Train Model ===
def train_model(features: pd.DataFrame, targets: pd.DataFrame):
    num_rows = len(features)
    weights = np.linspace(1, 3, num=num_rows)

    base_model = xgb.XGBRegressor(
        objective='reg:squarederror',
        learning_rate=0.07,
        n_estimators=350,
        max_depth=5,
        subsample=0.85,
        colsample_bytree=0.85,
        reg_alpha=0.05,
        reg_lambda=0.7
    )

    model = MultiOutputRegressor(base_model)
    model.fit(features, targets, sample_weight=weights)

    return model, weights


# === Save Models (simplified to use joblib for MultiOutputRegressor) ===


def save_multioutput_model(model: MultiOutputRegressor, model_path: str):
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    joblib.dump(model, model_path)
    print(f"Model saved to {model_path}")


def load_multioutput_model(model_path: str):
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found at {model_path}")
    model = joblib.load(model_path)
    print(f"Model loaded from {model_path}")
    return model
