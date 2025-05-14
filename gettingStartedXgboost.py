import pandas as pd
from sklearn.model_selection import train_test_split
import xgboost as xgb
# Import relevant metrics
from sklearn.metrics import mean_squared_error, r2_score, accuracy_score, classification_report

# 1. Load Data
try:
    df = pd.read_csv('baseball_stats.csv', encoding='windows-1252')
    df = df.drop(columns=['Player', 'Team', 'Lg', 'WAR', 'Pos', 'Awards'])
except FileNotFoundError:
    print("Error: CSV file not found.")
    exit()

target_column_index = 15

# 2. Identify Features (X) and Target (y)
if target_column_index >= len(df.columns):
    print(f"Error: Column at index {target_column_index} does not exist.")
    exit()

y = df.iloc[:, target_column_index]  # Target variable (the 19th column)
# All other columns as features
X = df.drop(df.columns[target_column_index], axis=1)

# 3. Split Data into Training and Testing Sets
X_train, X_test, y_train, y_test = train_test_split(
    # You can adjust test_size and random_state
    X, y, test_size=0.2, random_state=42)

# 4. Initialize and Train the XGBoost Model
# Determine if it's a regression or classification task based on the target variable
if pd.api.types.is_numeric_dtype(y):
    # Regression task
    # Or other regression objectives
    model = xgb.XGBRegressor(objective='reg:squarederror')
    model.fit(X_train, y_train)
else:
    # Classification task
    # You might need to handle class imbalances or multi-class scenarios
    model = xgb.XGBClassifier(objective='multi:softmax' if y.nunique(
    ) > 2 else 'binary:logistic')  # Or other classification objectives
    model.fit(X_train, y_train)

# 4.5 Save the model
model.save_model("predict_BA.json")

# 5. Make Predictions on the Test Set
predictions = model.predict(X_test)

# 6. Evaluate the Model
print("\n--- Model Evaluation ---")
if pd.api.types.is_numeric_dtype(y):
    # Regression metrics
    mse = mean_squared_error(y_test, predictions)
    r2 = r2_score(y_test, predictions)
    print(f"Mean Squared Error: {mse:.4f}")
    print(f"R-squared: {r2:.4f}")
else:
    # Classification metrics
    accuracy = accuracy_score(y_test, predictions)
    report = classification_report(y_test, predictions)
    print(f"Accuracy: {accuracy:.4f}")
    print("Classification Report:\n", report)
