
#### Backend (Python: Flask + Dash)
- Install Python
- In a terminal, go to `backend/`
- Install deps: `pip install -r requirements.txt` or `pip install flask flask-cors dash pandas paramiko PyJWT python-dotenv`
- Create `backend/.env`:
```bash
JWT_SECRET=change-me-strong
UNB_HOST=lambda.int.unb.ca
UNB_PORT=22
```
- Run server: `python app.py` (backend runs at 127.0.0.1:8000)

#### Frontend (React + Vite)
- Install Node.js
- In a terminal, go to `frontend/`
- Install deps: `npm i`
- Run server: `npm run dev` (frontend runs at http://localhost:5173)

#### Demo/Testing
- In a browser, open `http://localhost:5173/login`
- Username: your name
- Password: your password
- On success, you will be redirected to `/dataset`
