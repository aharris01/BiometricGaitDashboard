# backend/app.py
import os, time, jwt, paramiko
from functools import wraps
from flask import Flask, jsonify, request
from flask_cors import CORS
import dash
from dash import html, dcc
import pandas as pd
from dotenv import load_dotenv
load_dotenv()  # loads variables from backend/.env

# --- Config ---
UNB_HOST = os.environ.get("UNB_HOST", "lambda.int.unb.ca")
UNB_PORT = int(os.environ.get("UNB_PORT", "22"))
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-me")
JWT_ISS = "engg4000-auth"
JWT_EXP_SECONDS = 3600

server = Flask(__name__)
CORS(server)

# --- Auth helpers ---
def issue_token(sub: str):
    now = int(time.time())
    payload = {"sub": sub, "iss": JWT_ISS, "iat": now, "exp": now + JWT_EXP_SECONDS, "scope": ["dataset:read"]}
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "Missing token"}), 401
        token = auth.split(" ", 1)[1]
        try:
            jwt.decode(token, JWT_SECRET, algorithms=["HS256"], issuer=JWT_ISS)
        except Exception:
            return jsonify({"error": "Invalid/expired token"}), 401
        return f(*args, **kwargs)
    return wrapper

# --- Health (open) ---
@server.get("/api/health")
def health():
    return jsonify({"status":"ok"})

# --- SSH login against UNB lambda host; returns JWT on success ---
@server.post("/auth/unb-login")
def unb_login():
    data = request.get_json(force=True) or {}
    username = (data.get("id") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return jsonify({"error":"Missing credentials"}), 400

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            hostname=UNB_HOST, port=UNB_PORT, username=username, password=password,
            look_for_keys=False, allow_agent=False, timeout=6, auth_timeout=6, banner_timeout=6
        )
    except Exception:
        return jsonify({"error":"Invalid username or password"}), 401
    finally:
        try: client.close()
        except Exception: pass

    token = issue_token(username)
    return jsonify({"token": token})

# --- Example protected API ---
@server.get("/api/samples")
@require_auth
def samples():
    df = pd.DataFrame({"id":[1,2,3], "name":["A","B","C"], "value":[10,20,30]})
    return jsonify(df.to_dict(orient="records"))

# --- Optional Dash page ---
dash_app = dash.Dash(__name__, server=server, url_base_pathname="/dash/")
dash_app.layout = html.Div([
    html.H2("Dash diagnostics"),
    dcc.Markdown("Backend is up; try GET /api/health and POST /auth/unb-login.")
])

if __name__ == "__main__":
    # set envs before running in dev if you want:
    # export JWT_SECRET="a-very-strong-secret"
    # export UNB_HOST="lambda.int.unb.ca"
    server.run(host="127.0.0.1", port=8000, debug=True)
