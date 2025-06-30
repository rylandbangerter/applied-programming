// server.js
const express = require("express");
const multer = require("multer");
const path = require("path");
const fs = require("fs");
const admin = require("firebase-admin");
const cors = require("cors");

const app = express();

// Parse JSON request bodies
app.use(express.json());

// CORS: Allow your specific Netlify frontend URL
app.use(cors({
  origin: "https://685c3bc628567b00087470c5--merry-gnome-9ee3d2.netlify.app",
  methods: ["GET", "POST"],
  credentials: true
}));

// Initialize Firebase Admin SDK
const serviceAccount = JSON.parse(process.env.serviceAccountKey);
admin.initializeApp({
  credential: admin.credential.cert(serviceAccount),
});
const db = admin.firestore();

// File upload config
const upload = multer({ dest: "scraped_files/" });

// CSV parsing function
function parseCSVWithHeaderFix(csvText, placeholder = "@/H") {
  const lines = csvText.trim().split("\n");
  let headers = lines[0].split(",").map((h, i) => h.trim() || `${placeholder}_${i}`);
  const rows = lines.slice(1).map(line => {
    const values = line.split(",");
    const rowObj = {};
    headers.forEach((header, i) => {
      rowObj[header] = values[i] ? values[i].trim() : "";
    });
    return rowObj;
  });
  return rows.slice(0, -1);
}

// Upload CSV and store data in Firestore
async function uploadCSVFile(filePath, fileName) {
  const csvText = fs.readFileSync(filePath, "utf8");
  const dataRows = parseCSVWithHeaderFix(csvText);

  for (const row of dataRows) {
    const date = row["Date"] || row["date"] || row[Object.keys(row)[0]];
    const docName = `${fileName.replace(".csv", "")}_${date}`;
    const docRef = db.collection("gameStats").doc(docName);
    const docSnap = await docRef.get();

    if (!docSnap.exists) {
      await docRef.set(row);
      console.log(`Uploaded: ${docName}`);
    } else {
      console.log(`Skipped (exists): ${docName}`);
    }

    if (row["Player"]) {
      const [firstName, ...rest] = row["Player"].split(" ");
      const lastName = rest.join(" ");
      const playerId = row["Player"].toLowerCase().replace(/\s+/g, "_");
      await db.collection("playerData").doc(playerId).set({
        first_name: firstName,
        last_name: lastName
      }, { merge: true });
    }
  }
}

// Route: upload CSV file
app.post("/upload", upload.single("file"), async (req, res) => {
  const file = req.file;
  if (!file) return res.status(400).send("No file uploaded");

  try {
    await uploadCSVFile(file.path, file.originalname);
    fs.unlinkSync(file.path); // delete file after processing
    res.status(200).send("Upload successful");
  } catch (err) {
    console.error("Upload error:", err);
    res.status(500).send("Server error");
  }
});

// 🔥 Route: predict stat
app.post("/predict", (req, res) => {
  const { stat, player, opponent } = req.body;

  if (!stat || !player || !opponent) {
    return res.status(400).json({ error: "Missing stat, player, or opponent" });
  }

  console.log(`Prediction requested: Player=${player}, Stat=${stat}, Opponent=${opponent}`);

  // Replace this with real logic later
  const mockPrediction = (Math.random() * 5).toFixed(2);

  res.status(200).json({
    prediction: mockPrediction,
    player,
    stat,
    opponent
  });
});

// Start server
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
