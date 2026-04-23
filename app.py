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
<p style=\"margin-top:24px;\">Login successful.</p>
<p>Your registration details are now captured in the backend.</p>
<p><a href=\"/users\">View Registered Users</a></p>

</body>
</html>
"""
