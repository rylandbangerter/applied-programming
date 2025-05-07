import pandas as pd
import xgboost as xgb
import math
from sklearn.metrics import mean_squared_error, r2_score


# 1. Load the data
df = pd.read_csv("Shohei Ohtani Last Season.csv")

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


