// Import the functions you need from the SDKs you need
import { initializeApp } from "https://www.gstatic.com/firebasejs/9.22.2/firebase-app.js";
import { getAnalytics } from "https://www.gstatic.com/firebasejs/9.22.2/firebase-analytics.js";
import { getFirestore, collection, getDocs, doc, setDoc } from "https://www.gstatic.com/firebasejs/9.22.2/firebase-firestore.js";
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries
// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
    apiKey: "AIzaSyCL_Po7HXEyKAKDsLvoSCNy-Bb9NPmFxCo",
    authDomain: "moneyball-a1cab.firebaseapp.com",
    projectId: "moneyball-a1cab",
    storageBucket: "moneyball-a1cab.firebasestorage.app",
    messagingSenderId: "1002557739869",
    appId: "1:1002557739869:web:a035e6b37226a8e7560eb4",
    measurementId: "G-Q25HCXCHC6"
};

// // Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);
const db = getFirestore(app);

async function getPlayer() {
    const dropdown = document.getElementById("playerDropdown");

    try {
        const querySnapshot = await getDocs(collection(db, "playerData"));
        console.log("Data fetched:", querySnapshot.size, "documents found.");

        querySnapshot.forEach((doc) => {
        const data = doc.data();
        const fullName = `${data.first_name} ${data.last_name}`;

        // Create option element
        const formattedValue = fullName.toLowerCase().replace(/\s+/g, "_");
        const option = document.createElement("option");
        option.value = formattedValue;      // backend-friendly
        option.textContent = fullName;      // user-friendly

        dropdown.appendChild(option);
        });
    } catch (error) {
        console.error("Error fetching player data:", error);
    }
}

getPlayer();

async function getStats() {
    const dropdown = document.getElementById("statsDropdown");

    try {
        const querySnapshot = await getDocs(collection(db, "stats"));
        console.log("Data fetched:", querySnapshot.size, "documents found.");

        querySnapshot.forEach((doc) => {
        const data = doc.data();
        const statId = doc.id;
        const statName = data.name || statId;

        const option = document.createElement("option");
        option.value = statId; // sends just "H", "HR", etc. to backend
        option.textContent = `${statId} (${statName})`; // shows "H (Hits)" in dropdown

        dropdown.appendChild(option);
        });
    } catch (error) {
        console.error("Error fetching stat data:", error);
    }
}

getStats();

async function getOpponents() {
    const dropdown = document.getElementById("opponentDropdown");

    try {
        const querySnapshot = await getDocs(collection(db, "teams"));
        console.log("Data fetched:", querySnapshot.size, "documents found.");

        querySnapshot.forEach((doc) => {
        const data = doc.data();
        const teamId = doc.id;
        const city = data.city || "";
        const name = data.name || "";

        const option = document.createElement("option");
        option.value = teamId; // sends just "DET", "LAD", etc. to backend
        option.textContent = `${teamId} (${city} ${name})`.trim(); // shows "DET (Detroit Tigers)"

        dropdown.appendChild(option);
        });
    } catch (error) {
        console.error("Error fetching stat data:", error);
    }
}

getOpponents();

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

document.getElementById("predictButton").addEventListener("click", getPrediction);