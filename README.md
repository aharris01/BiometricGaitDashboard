## Project Overview
The **Biometric Gait Dashboard** is an interactive platform for analyzing and visualizing gait biometrics using data collected from pressure tiles recording.
The system enables:
- Secure user authentication through AWS Lambda (UNB login verification)
- Automatic extraction of individual footsteps from raw pressure data
- Data visualization through a React + Dash web interface
- Integration of Python analytics with a modern frontend dashboard

## Repository Structure
.github/                → CI/CD workflows (GitHub Actions)
auth-lambda/            → AWS Lambda authentication function
backend/                → Flask + Dash backend server
  processing/           → Footstep extraction & analysis scripts
frontend/               → React (Vite) frontend dashboard
notebooks/              → Jupyter notebooks for data exploration
environment.yml         → Conda environment for backend
.gitignore              → Ignore system & secret files
README.md               → Project documentation

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
