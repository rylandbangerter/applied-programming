import numpy as np
from sklearn.model_selection import train_test_split
import xgboost as xgb

model_name = input(
    "Please enter the name of the file with the model you would like to use. ")

try:
    model = xgb.Booster(model_file=model_name)
except Exception as e:
    print(f"Error loading the model: {e}")
    exit()

num_features = model.feature_names if hasattr(model, 'feature_names') else None
if num_features:
    n_features = len(num_features)
else:
    n_features = 27

print(f"This model expects {n_features} input features.")

# Prompt the user for input
try:
    feature_values_str = input(
        f"Enter the {n_features} feature values separated by spaces: ")
    feature_values = [float(x) for x in feature_values_str.split()]

    if len(feature_values) != n_features:
        print(f"Error: Please enter exactly {n_features} feature values.")
        exit()

    # Convert the input to the DMatrix format that XGBoost uses
    dmatrix = xgb.DMatrix(
        np.array([feature_values]), feature_names=num_features)

    # Make the prediction
    prediction = model.predict(dmatrix)

    print("\nPrediction:", prediction)

except ValueError:
    print("Error: Please enter numeric values for the features.")
except KeyboardInterrupt:
    print("\nExiting...")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
