from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import pandas as pd

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Load your trained model
model = joblib.load("shohei_multioutput_model.pkl")

# Get expected feature columns for input alignment
expected_features = model.estimators_[0].feature_names_in_

# Define target stat names
target_stats = ['WAR','G','PA','AB','R','H','2B','3B','HR','RBI','SB','CS','BB','SO','BA','OBP','SLG','OPS','OPS+','rOBA','Rbat+','TB','GIDP','HBP','SH','SF','IBB','GG','AS','SS','MVP','Position']

@app.route("/predict", methods=["POST"])
def predict():
    input_data = request.json
    if not input_data:
        return jsonify({"error": "No input data provided"}), 400

    # Convert input dict to DataFrame
    df_input = pd.DataFrame([input_data])

    # One-hot encode and align to expected features
    df_input = pd.get_dummies(df_input).reindex(columns=expected_features, fill_value=0)

    # Predict with model
    prediction = model.predict(df_input)[0]

    # Format prediction
    prediction_dict = {stat: round(pred, 2) for stat, pred in zip(target_stats, prediction)}

    return jsonify({"prediction": prediction_dict})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
