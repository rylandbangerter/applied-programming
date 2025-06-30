// Import Firebase SDKs
import { initializeApp } from "https://www.gstatic.com/firebasejs/9.22.2/firebase-app.js";
import { getAnalytics } from "https://www.gstatic.com/firebasejs/9.22.2/firebase-analytics.js";
import { getFirestore, collection, getDocs } from "https://www.gstatic.com/firebasejs/9.22.2/firebase-firestore.js";

// Firebase config
const firebaseConfig = {
    apiKey: "AIzaSyCL_Po7HXEyKAKDsLvoSCNy-Bb9NPmFxCo",
    authDomain: "moneyball-a1cab.firebaseapp.com",
    projectId: "moneyball-a1cab",
    storageBucket: "moneyball-a1cab.appspot.com",
    messagingSenderId: "1002557739869",
    appId: "1:1002557739869:web:a035e6b37226a8e7560eb4",
    measurementId: "G-Q25HCXCHC6"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);
const db = getFirestore(app);

// Populate Player Dropdown
async function getPlayer() {
    const dropdown = document.getElementById("playerDropdown");
    try {
        const querySnapshot = await getDocs(collection(db, "playerData"));
        querySnapshot.forEach((doc) => {
            const data = doc.data();
            const fullName = `${data.first_name} ${data.last_name}`;
            const formattedValue = fullName.toLowerCase().replace(/\s+/g, "_");

            const option = document.createElement("option");
            option.value = formattedValue;
            option.textContent = fullName;
            dropdown.appendChild(option);
        });
    } catch (error) {
        console.error("Error fetching player data:", error);
    }
}

// Populate Stat Dropdown
async function getStats() {
    const dropdown = document.getElementById("statsDropdown");
    try {
        const querySnapshot = await getDocs(collection(db, "stats"));
        querySnapshot.forEach((doc) => {
            const data = doc.data();
            const statId = doc.id;
            const statName = data.name || statId;

            const option = document.createElement("option");
            option.value = statId;
            option.textContent = `${statId} (${statName})`;
            dropdown.appendChild(option);
        });
    } catch (error) {
        console.error("Error fetching stat data:", error);
    }
}

// Populate Opponent Dropdown
async function getOpponents() {
    const dropdown = document.getElementById("opponentDropdown");
    try {
        const querySnapshot = await getDocs(collection(db, "teams"));
        querySnapshot.forEach((doc) => {
            const data = doc.data();
            const teamId = doc.id;
            const city = data.city || "";
            const name = data.name || "";

            const option = document.createElement("option");
            option.value = teamId;
            option.textContent = `${teamId} (${city} ${name})`.trim();
            dropdown.appendChild(option);
        });
    } catch (error) {
        console.error("Error fetching team data:", error);
    }
}

// Predict Function
async function getPrediction() {
    const stat = document.getElementById("statsDropdown").value;
    const player = document.getElementById("playerDropdown").value;
    const opponent = document.getElementById("opponentDropdown").value;
    const resultDiv = document.getElementById("predictionResults");

    const formattedPlayer = player.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
    resultDiv.innerHTML = `<strong>${formattedPlayer} — ${stat} Prediction vs ${opponent}:</strong>`;

    if ([stat, player, opponent].includes("choose")) {
        resultDiv.textContent = "Please select all fields before predicting.";
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
            resultDiv.textContent = `Server error: ${data.error}`;
            return;
        }

        resultDiv.innerHTML = `<p><strong>${formattedPlayer} — ${stat} Prediction vs ${opponent}:</strong></p>`;
        for (const [key, value] of Object.entries(data)) {
            resultDiv.innerHTML += `<p>${key.trim()}: ${value}</p>`;
        }
    } catch (err) {
        resultDiv.textContent = "Prediction failed. Check console.";
        console.error("Fetch error:", err);
    }
}

// Event Listener
document.getElementById("predictButton").addEventListener("click", getPrediction);

// Load all dropdowns
getPlayer();
getStats();
getOpponents();

// Wake up the backend when the page loads
async function wakeBackend() {
  try {
    await fetch("https://predictionbackend-m35t.onrender.com/");
    console.log("Backend wake-up ping sent");
  } catch (err) {
    console.error("Backend wake-up failed", err);
  }
}

wakeBackend(); // Call immediately on page load
