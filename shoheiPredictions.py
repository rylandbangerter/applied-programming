import pandas as pd
import xgboost as xgb
import math
from sklearn.metrics import mean_squared_error, r2_score
# connecting the python file to the html

from flask import Flask, request, jsonify
import joblib

app = Flask(__name__)
model = joblib.load("shohei_multioutput_model.pkl")

@app.route("/predict", methods=["POST"])
def predict():
    input_data = request.json
    df_input = pd.DataFrame([input_data])
    df_input = pd.get_dummies(df_input).reindex(columns=model.estimators_[0].feature_names_in_, fill_value=0)
    prediction = model.predict(df_input)[0]
    
    return jsonify({
        "prediction": {stat: round(pred, 2) for stat, pred in zip(['AB', 'R', 'H', 'HR', 'AVG'], prediction)}
    })

# 1. Load the data
df = pd.read_csv("Shohei_Ohtani_Last_Season.csv")

# 2. Drop non-numeric or non-useful columns
# Adjust as necessary based on your data
df = df.drop(columns=['Date', 'OPP', 'Team'], errors='ignore')



# 3. Set target and features
target_stats = ['AB','R','H','HR','AVG']  # AtBat, Runs, Hits, HomeRuns, AverageBattingScore


# Clean data 
features = df.drop(columns=target_stats, errors='ignore')
features = pd.get_dummies(features).fillna(0)

# Create an Input for the next game
next_game_features = features.mean().to_frame().T

# Ensure the next game input matches the columns
next_game_features = next_game_features[features.columns]

# Run Calculations on Target Stats
print("Shohei Ohtani's Next Game Results\n")
print(f"{'Stat':<10} {'Prediction':>10}")
print('-' * 21)
for stat in target_stats:
    if stat not in df.columns:
        print(f"X Stat '{stat}' not found. Skipping.")
        continue
    
    # Drop Rows where the stat is missing
    stat_df = df[df[stat].notna()]
    y = stat_df[stat]
    X = features.loc[stat_df.index]
    
    # 4. Train XGBoost regressor
    model = xgb.XGBRegressor(objective='reg:squarederror')
    model.fit(X, y)    
    
    # 5. Predict Hits in the next game
    prediction = model.predict(next_game_features)[0]

    # 6. Print results
    print(f"{stat:<10} {prediction:.2f}")

# Evaluate model on training data
train_preds = model.predict(X)
mse = mean_squared_error(y, train_preds)
r2 = r2_score(y, train_preds)
print(f"Training MSE: {mse:.2f}, R-Squared: {r2:.2f}")


