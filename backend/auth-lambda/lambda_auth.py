import json
import os
import time
import jwt  # PyJWT

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-me")
JWT_ISS = "engg4000-auth"
JWT_EXP_SECONDS = 3600

# DEV ONLY: single test user (replace with DynamoDB later)
USERS = { os.environ.get("AUTH_USER", "test"): os.environ.get("AUTH_PASS", "test123") }

def _resp(status, body, origin="*"):
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": True,
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "POST,OPTIONS",
        },
        "body": json.dumps(body),
    }

def handler(event, context):
    # CORS preflight
    method = event.get("requestContext", {}).get("http", {}).get("method") or event.get("httpMethod")
    if method == "OPTIONS":
        origin = event.get("headers", {}).get("origin", "*")
        return _resp(200, {"ok": True}, origin)

    origin = event.get("headers", {}).get("origin", "*")
    try:
        body = json.loads(event.get("body") or "{}")
        uid = (body.get("id") or "").strip()
        pw  = body.get("password") or ""

        if uid not in USERS or USERS[uid] != pw:
            return _resp(401, {"error":"Invalid credentials"}, origin)

        now = int(time.time())
        payload = {"sub": uid, "iss": JWT_ISS, "iat": now, "exp": now + JWT_EXP_SECONDS, "scope":["dataset:read"]}
        token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        return _resp(200, {"token": token}, origin)

    except Exception:
        return _resp(401, {"error":"Auth error"}, origin)
