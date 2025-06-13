/*
Assuming you have a Python backend (e.g., Flask or FastAPI) running an AI model,
and it exposes an endpoint like POST /predict that returns a prediction.

This JS code adds a button and calls the backend to get a prediction.
*/

const button = document.createElement('button');
button.textContent = 'Predict Stat';
document.body.appendChild(button);

button.addEventListener('click', async () => {
    // Example payload, adjust as needed for the model
    const inputData = { feature1: 42, feature2: 3.14 };

    try {
        const response = await fetch('http://localhost:5000/predict', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(inputData)
        });
        const result = await response.json();
        alert('Predicted stat: ' + result.prediction);
    } catch (error) {
        alert('Error: ' + error.message);
    }
});

// This is for getting a prediction from the AI model that connects to the button and the backend 
async function getPrediction() {
      const playerId = document.getElementById('player').value;

      const response = await fetch('/predict', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ player_id: playerId })
      });

      const data = await response.json();

      if (data.prediction) {
        document.getElementById('result').innerText = `Predicted Stat: ${data.prediction}`;
      } else {
        document.getElementById('result').innerText = `Error: ${data.error}`;
      }
    }