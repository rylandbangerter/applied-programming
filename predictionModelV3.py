import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.multioutput import MultiOutputRegressor
from sklearn.model_selection import KFold
from sklearn.metrics import mean_squared_error, r2_score
import os
import re

# Retrieve the firebase key path from environment variables
firebase_key_path = os.environ.get("FIREBASE_KEY_PATH")
if not firebase_key_path:
    raise ValueError("No Firebase key path found. Please set FIREBASE_KEY_PATH in your environment or .env file.")

# ===  Firebase Setup ===
cred = credentials.Certificate(firebase_key_path)
firebase_admin.initialize_app(cred)
db = firestore.client()

# === Lagged Features ===
def add_lagged_features(df, stats, lags=[1, 3], lag_weights={1: 1.2, 3: 1.1}, rolling_weight=1.3):
    for stat in stats:
        for lag in lags:
            column_name = f'{stat}_lag{lag}'
            df[column_name] = df[stat].shift(lag)

            # Apply weighting to lagged features
            df[column_name] *= lag_weights.get(lag, 1)  # Default weight = 1 if lag isn't specified
        
        # Add rolling average over last 3 games
        rolling_name = f'{stat}_rolling3'
        df[rolling_name] = df[stat].rolling(3).mean().shift(1)

        # Apply weighting to rolling average features
        df[rolling_name] *= rolling_weight

    return df

# ===  Load and Clean Player Data ===
def fetch_and_clean_player_data(player_name, selected_stat):
    docs = db.collection("gameStats").stream()
    cleaned_data = []

    for doc in docs:
        doc_id = doc.id
        if not doc_id.startswith(player_name):
            continue  # Skip other players

        raw = doc.to_dict()
        cleaned = {}

        for key, val in raw.items():
            val = str(val).strip()
            if re.match(r'^-?\d+\.?\d*%$', val):  # percent values
                cleaned[key] = float(val.replace('%', '')) / 100
            elif re.match(r'^-?\d+\.?\d*$', val):  # numeric values
                cleaned[key] = float(val)
            else:
                cleaned[key] = val  # categorical or other

        cleaned_data.append(cleaned)

    if not cleaned_data:
        raise ValueError(f"No data found for player: {player_name}")

    df = pd.DataFrame(cleaned_data)
    df = df.fillna(0)

    # === Normalize column names for consistency ===
    # Fix position column name dynamically
    pos_col = [col for col in df.columns if "Pos" in col]
    if pos_col:
        df.rename(columns={pos_col[0]: "Pos"}, inplace=True)
        df["Pos"] = df["Pos"].str.strip().replace({'\r': '', '\n': ''}, regex=True)

    # Normalize Opponent column and fill missing values
    if "Opp" in df.columns:
        df["Opp"] = df["Opp"].str.strip().replace({'\r': '', '\n': '', ' ': ''}, regex=True)
        df["Opp"].fillna("Unknown", inplace=True)

    # Convert selected columns from strings to floats
    numeric_cols = ['OBP', 'OPS', 'SLG', 'BA']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # === Add lagged features for the selected target stat ===
    target_stats = [selected_stat]
    df = add_lagged_features(df, target_stats, lags=[1, 3])

    # Drop incomplete lagged rows
    df = df.dropna().reset_index(drop=True)

    print(f"Loaded {len(cleaned_data)} games for {player_name}")
    return df

# ===  Define Features and Targets ===
def prepare_features_and_targets(df, selected_stat):
    # Define target stats to predict
    target_stats = [selected_stat]

    # Drop columns we do not want to use for features
    drop_cols = ['Date', 'Result', 'Team','DFS(DK)','DFS(FD)','WPA','cWPA','aLI','acLI','RE24','Rk','Inngs','Pos','Gtm','Gcar','@/H','BOP','IBB','HBP','SH','SF','CS']
    
    df = df.drop(columns=[col for col in drop_cols if col in df.columns], errors='ignore')
    
    features = df.copy()
    
    # Split and rejoin numeric + categorical features properly
    numeric = features.select_dtypes(include=['float64', 'int64'])
    categorical = features.select_dtypes(exclude=['float64', 'int64'])
    
    # Encode categorical data if it exsists
    if not categorical.empty:
        categorical = pd.get_dummies(categorical, drop_first=True)
    
    features = categorical.join(numeric).fillna(0)

    # Convert to numeric values
    targets = df[target_stats].apply(pd.to_numeric, errors='coerce').fillna(0)

    return features, targets, target_stats

# === Select Opponent ===
def add_user_input_opponent(features, user_opponent):
    # Identify the last row (the one used for prediction)
    pred_idx = features.index[-1]
    
    # Reset all opponent columns only for the prediction row
    for col in features.columns:
        if col.startswith('Opp_'):
            features.at[pred_idx, col] = False

    # Set the selected opponent column to True only for the prediction row
    opp_col = f'Opp_{user_opponent}'
    if opp_col in features.columns:
        features.at[pred_idx, opp_col] = True
    else:
        print(f"Warning: Opponent '{user_opponent}' not found in feature set.")

    return features

# === Weighted Opponent Stat ===
def add_opponent_lagged_stats(df, stat, opponent):
    
    opponent_col = f'Opp_{opponent}'
    
    #print("Available columns:", df.columns.tolist())  # Debugging: List all available columns
    #if "Opp_SEA" in df.columns:
    #    print(f"Total games where Opp_SEA is True: {df['Opp_SEA'].sum()}")
    #else:
    #    print("Warning: 'Opp_SEA' column is missing in df.")

    # Ensure the opponent column exists
    if opponent_col not in df.columns:
        raise ValueError(f"Opponent column '{opponent_col}' not found in DataFrame. Available columns: {df.columns.tolist()}")

    # Filter games played against this opponent
    opp_games = df[df[opponent_col] == True]
    
    # Apply lagged statistics
    for lag in [1, 3, 5]:
        df[f'{stat}_vs_{opponent}_lag{lag}'] = opp_games[stat].shift(lag)

    return df


# ===  Train Model ===
def train_model(features, targets):
    num_rows = len(features)
    weights = np.linspace(1, 3, num=num_rows)  # emphasize recent games

    base_model = xgb.XGBRegressor(
        objective='reg:squarederror',
        learning_rate=0.07,         # smaller step size for better generalization
        n_estimators=350,           # more trees to give it room to learn
        max_depth=5,                # slightly deeper trees to capture interactions
        subsample=0.85,              # inject a bit of randomness to help generalization
        colsample_bytree=0.85,       # sample features per tree to reduce overfitting
        reg_alpha=0.05,              # slight L1 regularization
        reg_lambda=0.7                # L2 regularization
    )

    model = MultiOutputRegressor(base_model)
    model.fit(features, targets, sample_weight=weights)

    return model, weights

# ===  Walk-Forward Validation Follows more real world predictions ===
def walk_forward_validation(features, targets, weights, window=10, val_window=5):
    r2_scores = []

    for i in range(window, len(features) - val_window):
        X_train = features.iloc[:i]
        y_train = targets.iloc[:i]
        w_train = weights[:i]

        X_val = features.iloc[i:i + val_window]
        y_val = targets.iloc[i:i + val_window]

        model = MultiOutputRegressor(xgb.XGBRegressor(objective='reg:squarederror'))
        model.fit(X_train, y_train, sample_weight=w_train)

        y_pred = model.predict(X_val)
        r2 = r2_score(y_val, y_pred, multioutput='uniform_average')
        r2_scores.append(r2)

    print("\nWalk-Forward R2 Scores (windowed):", r2_scores)
    print("Average R2:", np.mean(r2_scores))
# ===  Save Models ===
def save_models(model, target_stats):
    os.makedirs("xgb_json_models_v3", exist_ok=True)
    for i, est in enumerate(model.estimators_):
        est.get_booster().save_model(f"xgb_json_models_v3/{target_stats[i]}.json")

# ===  Predict Next Game ===
def predict_next_game(model, features, target_stats):
    next_game_input = features.iloc[[-1]]
    prediction = model.predict(next_game_input)[0]

    print("\nPredicted Next Game Stats:")
    print(f"{'Stat':<8} {'Prediction':>10}")
    print('-' * 20)
    for stat, val in zip(target_stats, prediction):
        print(f"{stat:<8} {val:>10.3f}")

# ===  Main Execution ===
if __name__ == "__main__":
    player_name = "Jose_Altuve"  # Replace this later with user input from HTML
    selected_stat = "TB" # This will come from HTML input
    opponent = "SEA"
    df = fetch_and_clean_player_data(player_name, selected_stat)
    #This Print Statement is for checking if all the values are being found
    #print("Jose Altuve data sample:\n", df.head(1).T)
    features, targets, target_stats = prepare_features_and_targets(df, selected_stat)
    features = add_user_input_opponent(features, opponent)
    features = add_opponent_lagged_stats(features, selected_stat, opponent)

    model, weights = train_model(features, targets)
    #This is only for evluating the model, To see evaluation score uncomment this function
    #walk_forward_validation(features, targets, weights, window=10, val_window=5)
    save_models(model, target_stats)
    print('Audit the last 5 Rows\n----------')
    print(df[['Date', 'TB', 'H', 'R','AB']].tail())
    print("\nLatest input used for prediction:\n", features.iloc[[-1]].T)
    predict_next_game(model, features, target_stats)

    # Optional: Show training performance
    #train_preds = model.predict(features)
    #print(f"\nTraining MSE: {mean_squared_error(targets, train_preds):.2f}")
    #print(f"Training R2: {r2_score(targets, train_preds):.2f}")
    
    tb_model = model.estimators_[target_stats.index('TB')]
    importances = tb_model.feature_importances_
    tb_features = features.columns
    important_tb = pd.Series(importances, index=tb_features).sort_values(ascending=False)

    print("\nTop Features for TB Prediction:\n", important_tb.head(10))
    
    print("\nAverage TB in training data:", df["TB"].mean())
    print("TB distribution:\n", df["TB"].value_counts().sort_index())
    
    print("\nActual TB from last game:", df.iloc[-1]["TB"])
    
    cols = [c for c in features.columns if 'TB' in c]
    print("\nRecent TB-related features:\n", features[cols].tail())
    


