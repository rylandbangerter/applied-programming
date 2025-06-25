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
  const stat = document.getElementById("statsDropdown").value;
  const player = document.getElementById("playerDropdown").value;
  const opponent = document.getElementById("opponentDropdown").value;

  const displayBox = document.getElementById("predictionResults");

  // Clear out old prediction
  displayBox.innerHTML = "";

  if ([stat, player, opponent].includes("choose")) {
    displayBox.textContent = "Please select all fields before predicting.";
    return;
  }

  try {
    const response = await fetch("https://predictionbackend-m35t.onrender.com/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ stat, player, opponent }),
    });

    const data = await response.json();

    if (data.error) {
      displayBox.textContent = `Server error: ${data.error}`;
      return;
    }

    displayBox.innerHTML = `
      <p><strong>Player:</strong> ${player}</p>
      <p><strong>Stat:</strong> ${stat}</p>
      <p><strong>Opponent:</strong> ${opponent}</p>
      <p><strong>Prediction:</strong></p>
    `;

    for (const [key, value] of Object.entries(data)) {
      displayBox.innerHTML += `<p>${key}: ${value}</p>`;
    }
  } catch (err) {
    displayBox.textContent = "Prediction failed. Check console.";
    console.error("Fetch error:", err);
  }
}
