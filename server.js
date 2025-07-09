const express = require("express");
const multer = require("multer");
const fs = require("fs");
const fsPromises = fs.promises;
const admin = require("firebase-admin");
const cors = require("cors");

const app = express();
const PORT = process.env.PORT || 3001;

// Parse JSON request bodies
app.use(express.json());

// CORS: Allow your specific Netlify frontend URL
const allowedOrigins = [
  "https://6865611a383dca00083d9596--merry-gnome-9ee3d2.netlify.app",
  "https://686561b3246d350008c802e1--merry-gnome-9ee3d2.netlify.app",
  "https://686e9fc6cd75530008632a49--merry-gnome-9ee3d2.netlify.app/mbgpt/"
  // add any other Netlify frontend URLs you use here
];

app.use(cors({ 
  origin: function(origin, callback) {
    if (!origin) return callback(null, true); // allow non-browser tools like Postman
    if (allowedOrigins.indexOf(origin) === -1) {
      const msg = `The CORS policy does not allow access from origin: ${origin}`;
      return callback(new Error(msg), false);
    }
    return callback(null, true);
  },
  methods: ["GET", "POST"],
  credentials: true
}));



// Initialize Firebase Admin SDK safely
let serviceAccount = require("firebase-key.json");



admin.initializeApp({
  credential: admin.credential.cert(serviceAccount),
});
const db = admin.firestore();

// File upload config with size limit (5 MB)
const upload = multer({
  dest: "scraped_files/",
  limits: { fileSize: 5 * 1024 * 1024 }
});

// CSV parsing function
function parseCSVWithHeaderFix(csvText, placeholder = "@/H") {
  const lines = csvText.trim().split("\n");
  const headers = lines[0].split(",").map((h, i) => h.trim() || `${placeholder}_${i}`);
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
    //const docSnap = await docRef.get();
    await docRef.set(row);
    console.log(`Uploaded: ${docName}`);

    // if (!docSnap.exists) {
     
    // } else {
    //   console.log(`Skipped (exists): ${docName}`);
    // }

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
    try {
      await fsPromises.unlink(file.path);
    } catch (err) {
      console.error("Failed to delete file:", err);
    }
    res.status(200).send("Upload successful");
  } catch (err) {
    console.error("Upload error:", err);
    res.status(500).send("Server error");
  }
});

// Route: predict stat
app.post("/predict", async (req, res) => {
  try {
    const { stat, player, opponent } = req.body;

    if (!stat || !player || !opponent) {
      return res.status(400).json({ error: "Missing stat, player, or opponent" });
    }

    console.log(`Prediction requested: Player=${player}, Stat=${stat}, Opponent=${opponent}`);

    // TODO: Replace this with real prediction logic
    const mockPrediction = (Math.random() * 5).toFixed(2);

    res.status(200).json({
      prediction: mockPrediction,
      player,
      stat,
      opponent
    });
  } catch (err) {
    console.error("Prediction error:", err);
    res.status(500).json({ error: "Server error" });
  }
});

// Root route — for wake-up ping
app.get("/", (req, res) => {
  res.status(200).send("Backend is awake!");
});

// Handle 404 for unknown routes
app.use((req, res) => {
  res.status(404).json({ error: "Not found" });
});

// Generic error handler
app.use((err, req, res, next) => {
  console.error("Unhandled error:", err);
  res.status(500).json({ error: "Internal server error" });
});

const path = require("path");

async function processExistingCSVs() {
  const files = await fsPromises.readdir("scraped_files/");
  for (const file of files) {
    if (file.endsWith(".csv")) {
      const filePath = path.join("scraped_files", file);
      try {
        await uploadCSVFile(filePath, file);
        await fsPromises.unlink(filePath);
        console.log(`Processed and deleted: ${file}`);
      } catch (err) {
        console.error(`Failed processing ${file}:`, err);
      }
    }
  }
}

processExistingCSVs();

// Start server
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
