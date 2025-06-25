const fs = require("fs");
const path = require("path");
const admin = require("firebase-admin");

const serviceAccount = require("./serviceAccountKey.json");

admin.initializeApp({
  credential: admin.credential.cert(serviceAccount),
});

const db = admin.firestore();

const csvFolder = "scraped_files/";

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

async function uploadCSVFile(filePath, fileName) {
  try {
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
    }
  } catch (err) {
    console.error(`Error processing ${fileName}:`, err);
  }
}

async function processCSVFolder() {
  const files = fs.readdirSync(csvFolder).filter(f => f.endsWith(".csv"));

  for (const file of files) {
    const fullPath = path.join(csvFolder, file);
    await uploadCSVFile(fullPath, file);
    fs.unlinkSync(fullPath);
    console.log(`Deleted: ${file}`);
  }
}

processCSVFolder();
