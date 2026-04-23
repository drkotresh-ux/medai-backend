from datetime import datetime
from pathlib import Path
import csv
import tempfile

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel

app = FastAPI(title="MedAI Backend")

ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = Path("/var/data") if Path("/var/data").exists() else ROOT_DIR
PREDICTIONS_LOG_FILE = ROOT_DIR / "predictions_log.csv"
PREDICTIONS_LOG_FIELDS = ["timestamp", "age", "glucose", "bp", "prediction"]
USER_FILE = DATA_DIR / "users.csv"
USER_FILE_FALLBACK = Path(tempfile.gettempdir()) / "medai_users.csv"
USER_HEADERS = ["timestamp", "name", "phone", "email"]


class PatientData(BaseModel):
    age: int
    glucose: float
    bp: float


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/")
def home():
    return JSONResponse({"status": "MedAI Backend Running", "routes": ["/user (POST)", "/users (GET)", "/login (GET)", "/app (GET)", "/predict (POST)"]})


@app.get("/login", response_class=HTMLResponse)
def login_page():
    return """
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>MedAI Login</title>
</head>
<body style="text-align:center; margin-top:100px; font-family:Arial;">
<h2>MedAI Login</h2>
<input id="name" placeholder="Enter Name"><br><br>
<input id="phone" placeholder="Enter Phone"><br><br>
<input id="email" placeholder="Email (optional)"><br><br>
<button onclick="login()">Login</button>
<script>
async function login() {
  const name = document.getElementById("name").value.trim();
  const phone = document.getElementById("phone").value.trim();
  const email = document.getElementById("email").value.trim();
  if (!phone) { alert("Phone required"); return; }
  try {
    const res = await fetch("/user", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ name, phone, email })
    });
    if (res.ok) {
      alert("Saved");
      localStorage.setItem("user", JSON.stringify({ name, phone }));
      window.location.href = "/app";
    } else {
      const t = await res.text();
      alert("Failed: " + t);
    }
  } catch (e) { alert("Connection error"); }
}
</script>
</body>
</html>
"""


@app.post("/user")
def save_user(data: dict, request: Request):
    name = str(data.get("name", "")).strip()
    phone = str(data.get("phone", "")).strip()
    if not phone:
        raise HTTPException(status_code=400, detail="Phone required")
    row = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "name": name or phone,
        "phone": phone,
        "email": str(data.get("email", "")).strip(),
    }
    def _append_row(target_file: Path) -> None:
        file_exists = target_file.exists()
        with target_file.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=USER_HEADERS)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)
    try:
        _append_row(USER_FILE)
    except Exception:
        _append_row(USER_FILE_FALLBACK)
    response = JSONResponse({"status": "saved"})
    response.set_cookie(key="medai_auth", value="1", httponly=True, samesite="lax",
                        secure=(request.url.scheme == "https"), max_age=60 * 60 * 12)
    return response


@app.get("/users", response_class=PlainTextResponse)
def get_users():
    lines = []
    seen = set()
    def _read(path: Path):
        if not path.exists():
            return
        try:
            with path.open("r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    key = (row.get("timestamp",""), row.get("phone",""))
                    if key in seen:
                        continue
                    seen.add(key)
                    lines.append(",".join([row.get("timestamp",""), row.get("name",""), row.get("phone",""), row.get("email","")]))
        except Exception:
            pass
    _read(USER_FILE)
    _read(USER_FILE_FALLBACK)
    if not lines:
        return "No users yet"
    return "timestamp,name,phone,email\n" + "\n".join(lines)


@app.post("/logout")
def logout_user():
    response = JSONResponse({"status": "logged_out"})
    response.delete_cookie("medai_auth")
    return response


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
