from datetime import datetime
from pathlib import Path
import csv

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI(title="MedAI Backend")

ROOT_DIR = Path(__file__).resolve().parent
PREDICTIONS_LOG_FILE = ROOT_DIR / "predictions_log.csv"
PREDICTIONS_LOG_FIELDS = ["timestamp", "age", "glucose", "bp", "prediction"]


class PatientData(BaseModel):
    age: int
    glucose: float
    bp: float


@app.get("/")
def home():
    return {"message": "MedAI Backend Running"}


@app.get("/app", response_class=HTMLResponse)
def app_page():
    return """
<!DOCTYPE html>
<html>
<head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <title>MedAI Suite</title>
</head>
<body style=\"text-align:center; font-family:Arial; margin-top:100px;\">

<h1>MedAI Suite</h1>
<p>AI-Powered Clinical Decision Support</p>

<h3>Try Demo</h3>

<input id=\"age\" placeholder=\"Age\"><br><br>
<input id=\"glucose\" placeholder=\"Glucose\"><br><br>
<input id=\"bp\" placeholder=\"BP\"><br><br>

<button onclick=\"predict()\">Predict</button>

<p id=\"status\" style=\"color:#a63b00;\"></p>
<h2 id=\"result\"></h2>

<script>
async function predict() {
    const statusEl = document.getElementById(\"status\");
    const resultEl = document.getElementById(\"result\");
    statusEl.innerText = \"\";
    resultEl.innerText = \"\";

    const payload = {
        age: Number(age.value),
        glucose: Number(glucose.value),
        bp: Number(bp.value)
    };

    if (!Number.isFinite(payload.age) || !Number.isFinite(payload.glucose) || !Number.isFinite(payload.bp)) {
        statusEl.innerText = \"Please enter valid numbers\";
        return;
    }

    if (payload.age < 1 || payload.age > 120) {
        statusEl.innerText = \"Age should be between 1 and 120\";
        return;
    }

    if (payload.glucose < 40 || payload.glucose > 600) {
        statusEl.innerText = \"Glucose should be between 40 and 600\";
        return;
    }

    if (payload.bp < 40 || payload.bp > 250) {
        statusEl.innerText = \"BP should be between 40 and 250\";
        return;
    }

    statusEl.innerText = \"Predicting...\";

    try {
        const response = await fetch(\"/predict\", {
            method: \"POST\",
            headers: {\"Content-Type\": \"application/json\"},
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        if (!response.ok) {
            statusEl.innerText = data.detail || \"Prediction failed\";
            return;
        }

        resultEl.innerText = data.prediction || \"No result\";
        statusEl.innerText = \"\";
    } catch (error) {
        statusEl.innerText = \"Server not reachable. Try again.\";
    }
}
</script>

</body>
</html>
"""


@app.post("/predict")
def predict(data: PatientData):
    if data.age < 1 or data.age > 120:
        raise HTTPException(status_code=400, detail="Age should be between 1 and 120")
    if data.glucose < 40 or data.glucose > 600:
        raise HTTPException(status_code=400, detail="Glucose should be between 40 and 600")
    if data.bp < 40 or data.bp > 250:
        raise HTTPException(status_code=400, detail="BP should be between 40 and 250")

    # Temporary demo logic. Replace with your trained model inference later.
    risk = "High Risk" if data.glucose > 150 else "Low Risk"

    file_exists = PREDICTIONS_LOG_FILE.exists()
    with PREDICTIONS_LOG_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=PREDICTIONS_LOG_FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(
            {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "age": data.age,
                "glucose": data.glucose,
                "bp": data.bp,
                "prediction": risk,
            }
        )

    return {
        "prediction": risk,
        "input": data,
    }
