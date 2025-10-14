# backend/app.py
from flask import Flask, jsonify, request
from flask_cors import CORS
import dash
from dash import html, dcc
import pandas as pd

# Flask base app (Dash will mount on this)
server = Flask(__name__)
CORS(server)  # allow requests from the frontend during dev

# --- REST endpoints for React ---
@server.get("/api/health")
def health():
    return jsonify({"status": "ok"})

@server.get("/api/samples")
def samples():
    # Example data (replace with your real logic)
    df = pd.DataFrame({"id":[1,2,3], "name":["A","B","C"], "value":[10,20,30]})
    return jsonify(df.to_dict(orient="records"))

@server.post("/api/predict")
def predict():
    payload = request.get_json(force=True) or {}
    # do work... return a mock result
    return jsonify({"ok": True, "received": payload})

# --- Optional: Dash UI mounted at /dash ---
dash_app = dash.Dash(__name__, server=server, url_base_pathname="/dash/")
dash_app.layout = html.Div([
    html.H2("Dash diagnostics"),
    dcc.Markdown("This is an optional Dash page served by the backend."),
])

if __name__ == "__main__":
    server.run(host="127.0.0.1", port=8000, debug=True)
