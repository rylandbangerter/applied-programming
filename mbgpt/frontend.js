/*
Assuming you have a Python backend (e.g., Flask or FastAPI) running an AI model,
and it exposes an endpoint like POST /predict that returns a prediction.

This JS code adds a button and calls the backend to get a prediction.
*/


// This is for getting a prediction from the AI model that connects to the button and the backend
// async function getPrediction() {
//   const playerId = document.getElementById("player").value;

//   const response = await fetch("/predict", {
//     method: "POST",
//     headers: { "Content-Type": "application/json" },
//     body: JSON.stringify({ player_id: playerId }),
//   });

//   const data = await response.json();

//   if (data.prediction) {
//     document.getElementById(
//       "result"
//     ).innerText = `Predicted Stat: ${data.prediction}`;
//   } else {
//     document.getElementById("result").innerText = `Error: ${data.error}`;
//   }
// }

// Calling the Docker image
// fetch("http://localhost:5000/api/data")
//   .then((res) => res.json())
//   .then((data) => console.log(data));
//   const cors = require('cors');
// app.use(cors());


// running a python file in HTML 
  async function getPrediction() {
        const number = document.getElementById("numberInput").value;
        const response = await fetch("http://localhost:5000/predict", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ number }),
        });
        const data = await response.json();
        document.getElementById("result").textContent =
          "Prediction: " + data.prediction;
  }
  async function getPrediction() {
    const response = await fetch("http://localhost:5000/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ request: "predictStats" }), // placeholder
    });

    const data = await response.json();
    const resultDiv = document.getElementById("result");

    if (data) {
      resultDiv.innerHTML = "<strong>Predicted Stats:</strong><br>";
      for (const [stat, value] of Object.entries(data)) {
        resultDiv.innerHTML += `${stat}: ${value}<br>`;
      }
    } else {
      resultDiv.textContent = "Error: Could not fetch predictions.";
    }
  }