import pandas as pd
import xgboost as xgb
from sklearn.multioutput import MultiOutputRegressor
from sklearn.model_selection import train_test_split, cross_val_score, KFold
from sklearn.metrics import mean_squared_error, r2_score
import numpy as np
import joblib

# 1. Load the data
df = pd.read_csv("Shohei_Ohtani_Last_Season.csv")

# 2. Drop non-numeric or non-useful columns
df = df.drop(columns=['Date', 'OPP', 'Team'], errors='ignore')

# 3. Define target and features
target_stats = ['AB', 'R', 'H', 'HR', 'AVG']
features = df.drop(columns=target_stats, errors='ignore')
features = pd.get_dummies(features).fillna(0)

targets = df[target_stats].fillna(0)

# 4. Create sample weights to emphasize recent games
num_rows = len(df)
weights = np.linspace(0.5, 1.5, num=num_rows)  # linear weighting

# 5. Train multi-output XGBoost regressor
base_model = xgb.XGBRegressor(objective='reg:squarederror')
model = MultiOutputRegressor(base_model)
model.fit(features, targets, sample_weight=weights)

# 6. Cross-validation evaluation
kf = KFold(n_splits=5, shuffle=True, random_state=42)
cv_r2_scores = []
for train_index, val_index in kf.split(features):
    X_train, X_val = features.iloc[train_index], features.iloc[val_index]
    y_train, y_val = targets.iloc[train_index], targets.iloc[val_index]
    w_train = weights[train_index]

    cv_model = MultiOutputRegressor(xgb.XGBRegressor(objective='reg:squarederror'))
    cv_model.fit(X_train, y_train, sample_weight=w_train)
    y_pred = cv_model.predict(X_val)
    r2 = r2_score(y_val, y_pred)
    cv_r2_scores.append(r2)

print("\nCross-Validation R2 Scores:", cv_r2_scores)
print("Average CV R2 Score:", np.mean(cv_r2_scores))

# 7. Save the trained model
joblib.dump(model, "shohei_multioutput_model.pkl")

# 8. Prepare input for next game (using the most recent row)
next_game_features = features.iloc[[-1]]

# 9. Predict all stats
predictions = model.predict(next_game_features)[0]

print("\nShohei Ohtani's Next Game Results\n")
print(f"{'Stat':<10} {'Prediction':>10}")
print('-' * 21)
for stat, prediction in zip(target_stats, predictions):
    print(f"{stat:<10} {prediction:.2f}")

# 10. Evaluate model on training data
train_preds = model.predict(features)
mse = mean_squared_error(targets, train_preds)
r2 = r2_score(targets, train_preds)
print(f"\nTraining MSE: {mse:.2f}, R-Squared: {r2:.2f}")
