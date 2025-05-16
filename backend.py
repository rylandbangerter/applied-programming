# app.py
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, request, jsonify, render_template
import pickle


## This is just sample code so we would need to change it so that it works with our database and models.

# Init Flask
app = Flask(__name__)

# Init Firebase
cred = credentials.Certificate('path/to/your-firebase-key.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

# Load your AI model
model = pickle.load(open('useAnImportedModel.py', 'rb'))

@app.route('/')
def index():
    return render_template('frontend.html')

@app.route('/predict', methods=['POST'])
def predict():
    data = request.json
    player_id = data['player_id']

    # Get player data from Firestore (assume collection is "players")
    doc = db.collection('players').document(player_id).get()

    if not doc.exists:
        return jsonify({'error': 'Player not found'}), 404

    player_data = doc.to_dict()

    # Extract features the model needs (example: age, pa, ab, hr, rbi)
    features = [
        player_data.get('age', 0),
        player_data.get('pa', 0),
        player_data.get('ab', 0),
        player_data.get('hr', 0),
        player_data.get('rbi', 0)
    ]

    prediction = model.predict([features])[0]
    return jsonify({'prediction': prediction})
