# UAT Participant Setup Guide

## What you will receive
- A copy of the application repository
- A data subset folder named `data`

## Before you begin
- Install Python 3.11 on your machine
- On Windows, make sure **Add Python to PATH** is checked during installation

## 1. Verify Python is installed
- Open a terminal
- Run:

```bash
python --version
```

- Confirm that Python is available in the terminal

## 2. Place the project files on your machine
- Put the repository in a convenient folder, for example:

```text
C:\UAT\gait-dashboard
```

- Put the provided `data` folder somewhere on your machine, for example:

```text
C:\UAT\data
```

## 3. Confirm the data folder structure
- The provided `data` folder should already match this structure:

```text
<DATAROOT>/<participant>/<date>/<direction>/<event>/
```

- Example:

```text
C:\UAT\data\100\2023-09-15\in\7\
```

- The event folder should contain files such as:
  - `trial.npz`
  - `trial.p100.npz`
  - `trial.grf.npz`
  - `steps.npz`
  - `metadata.csv`

## 4. Open a terminal in the repository folder
- Example:

```bash
cd C:\UAT\gait-dashboard
```

## 5. Create a virtual environment
- Run:

```bash
python -m venv .venv
```

## 6. Activate the virtual environment
- On Windows Command Prompt, run:

```bash
.venv\Scripts\activate
```

- On Windows PowerShell, run:

```powershell
.venv\Scripts\Activate.ps1
```

## 7. Install the required packages
- Run:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## 8. Configure the `.env` file
- In the repository root, create or edit a file named `.env`
- Add a `DATAROOT` entry that points to the provided `data` folder itself
- Example if `data` is outside the repo:

```env
DATAROOT=C:\UAT\data
```

- Example if `data` is inside the repo folder:

```env
DATAROOT=data
```

## Important note about `DATAROOT`
- `DATAROOT` must point to the `data` folder itself
- It must not point to:
  - the parent folder above `data`
  - an individual participant folder inside `data`

## 9. Delete `local.db` before the first run
- In the repository folder, delete:

```text
local.db
```

- Do not delete:

```text
manifest.db
```

- This is a one-time first-run step so the local database can rebuild correctly on the participant’s machine

## 10. Start the application
- From the repository folder, run:

```bash
python main.py
```

## 11. Open the dashboard
- Once the application starts, open this address in a web browser:

```text
http://127.0.0.1:8050
```

## Normal startup after initial setup
- After the one-time setup is complete, starting the app should be as simple as:

```bash
cd C:\UAT\gait-dashboard
.venv\Scripts\activate
python main.py
```

## Troubleshooting
- If Python is not recognized:
  - Reinstall Python and ensure **Add Python to PATH** is enabled

- If the app opens but no data appears:
  - Check that `DATAROOT` points to the `data` folder
  - Check that the folder structure is:

```text
<DATAROOT>/<participant>/<date>/<direction>/<event>/
```

- If dependencies install very slowly:
  - Keep the install running if it is still progressing
  - Try:

```bash
python -m pip install --upgrade pip setuptools wheel
python -m pip install --prefer-binary -r requirements.txt
```

- If you still have issues starting the app:
  - Confirm that `.env` is present
  - Confirm that `local.db` was deleted before the first run
  - Confirm that you are running the command from the repository root

## Quick summary
- Put the repo on your machine
- Put the provided `data` folder on your machine
- Set `DATAROOT` in `.env` to the path of the `data` folder
- Delete `local.db` once
- Run:

```bash
python main.py
```