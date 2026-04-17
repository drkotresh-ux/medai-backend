from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI(title="MedAI Backend")


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

    const payload = {
        age: Number(age.value),
        glucose: Number(glucose.value),
        bp: Number(bp.value)
    };

    if (!Number.isFinite(payload.age) || !Number.isFinite(payload.glucose) || !Number.isFinite(payload.bp)) {
        statusEl.innerText = \"Please enter valid numbers\";
        resultEl.innerText = \"\";
        return;
    }

    statusEl.innerText = \"Predicting...\";

    const response = await fetch(\"/predict\", {
        method: \"POST\",
        headers: {\"Content-Type\": \"application/json\"},
        body: JSON.stringify(payload)
    });

    const data = await response.json();
    resultEl.innerText = data.prediction || \"No result\";
    statusEl.innerText = \"\";
}
</script>

</body>
</html>
"""


@app.post("/predict")
def predict(data: PatientData):
    # Temporary demo logic. Replace with your trained model inference later.
    risk = "High Risk" if data.glucose > 150 else "Low Risk"
    return {
        "prediction": risk,
        "input": data,
    }
