from datetime import datetime
from pathlib import Path
import sqlite3
import io
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, StreamingResponse
from openpyxl import Workbook

app = FastAPI(title="MedAI Backend")

# -----------------------
# CORS
# -----------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://medai-backend-0o14.onrender.com",
        "https://medaisuites.onrender.com",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------
# DATABASE
# -----------------------
DB_FILE = Path("/var/data/users.db") if Path("/var/data").exists() else Path("users.db")


def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            name TEXT,
            phone TEXT,
            email TEXT
        )
        """
    )

    conn.commit()
    conn.close()


init_db()

# -----------------------
# HEALTH
# -----------------------
@app.get("/health")
def health_check():
    return {"status": "ok"}


# -----------------------
# HOME
# -----------------------
@app.get("/")
def home():
    return {
        "status": "SQLITE VERSION LIVE NOW",
        "routes": ["/login", "/user", "/users", "/users.xlsx", "/debug-db"],
    }


@app.get("/debug-db")
def debug_db():
    return {
        "db_file": str(DB_FILE),
        "exists": DB_FILE.exists(),
    }


# -----------------------
# LOGIN PAGE
# -----------------------
@app.get("/login", response_class=HTMLResponse)
def login_page():
    return """
<!DOCTYPE html>
<html>
<head>
<title>MedAI Login</title>
</head>
<body style="text-align:center;margin-top:100px;font-family:Arial;">
<h2>MedAI Login</h2>

<input id="name" placeholder="Enter Name"><br><br>
<input id="phone" placeholder="Enter Phone"><br><br>
<input id="email" placeholder="Email (optional)"><br><br>

<button onclick="login()">Login</button>

<script>
async function login(){
 const name=document.getElementById("name").value.trim();
 const phone=document.getElementById("phone").value.trim();
 const email=document.getElementById("email").value.trim();

 if(!phone){
   alert("Phone required");
   return;
 }

 const res=await fetch("/user",{
   method:"POST",
   headers:{"Content-Type":"application/json"},
   body:JSON.stringify({name,phone,email})
 });

 if(res.ok){
   localStorage.setItem("user",JSON.stringify({name,phone}));
   window.location.href="/app";
 }else{
   alert("Failed");
 }
}
</script>

</body>
</html>
"""


# -----------------------
# SAVE USER
# -----------------------
@app.post("/user")
def save_user(data: dict, request: Request):
    name = str(data.get("name", "")).strip()
    phone = str(data.get("phone", "")).strip()
    email = str(data.get("email", "")).strip()

    if not phone:
        raise HTTPException(status_code=400, detail="Phone required")

    if not name:
        name = phone

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO users (timestamp,name,phone,email) VALUES (?,?,?,?)",
        (datetime.now().isoformat(timespec="seconds"), name, phone, email),
    )

    conn.commit()
    conn.close()

    response = JSONResponse({"status": "saved"})
    response.set_cookie(
        key="medai_auth",
        value="1",
        httponly=True,
        samesite="lax",
        secure=(request.url.scheme == "https"),
    )
    return response


# -----------------------
# APP PAGE
# -----------------------
@app.get("/app", response_class=HTMLResponse)
def app_page():
    return """
<html>
<body style="text-align:center;font-family:Arial;margin-top:100px;">
<h1>MedAI Suite</h1>
<p>Login successful</p>
<p><a href="/users">View Users</a></p>
<p><a href="/users.xlsx">Download Excel</a></p>
</body>
</html>
"""


@app.get("/access")
def access():
    return RedirectResponse("/app")


# -----------------------
# USERS VIEW
# -----------------------
@app.get("/users", response_class=PlainTextResponse)
def get_users():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    rows = cur.execute(
        """
        SELECT timestamp,name,phone,email
        FROM users
        ORDER BY id DESC
        LIMIT 300
        """
    ).fetchall()

    conn.close()

    if not rows:
        return "No users yet"

    lines = ["timestamp,name,phone,email"]

    for r in rows:
        lines.append(",".join([
            str(r[0]),
            str(r[1]),
            str(r[2]),
            str(r[3])
        ]))

    return "\n".join(lines)


# -----------------------
# EXCEL EXPORT
# -----------------------
@app.get("/users.xlsx")
def download_users_excel():
    wb = Workbook()
    ws = wb.active
    ws.title = "Users"

    ws.append(["Timestamp", "Name", "Phone", "Email"])

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    rows = cur.execute(
        """
        SELECT timestamp,name,phone,email
        FROM users
        ORDER BY id DESC
        """
    ).fetchall()

    conn.close()

    for row in rows:
        ws.append(list(row))

    excel_buffer = io.BytesIO()
    wb.save(excel_buffer)
    excel_buffer.seek(0)

    return StreamingResponse(
        iter([excel_buffer.getvalue()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition":
            "attachment; filename=medai_users.xlsx"
        }
    )
