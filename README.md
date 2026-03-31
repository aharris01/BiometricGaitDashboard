<!-- Improved compatibility of back to top link: See: https://github.com/othneildrew/Best-README-Template/pull/73 -->
<a id="readme-top"></a>
<!--
*** Thanks for checking out the Best-README-Template. If you have a suggestion
*** that would make this better, please fork the repo and create a pull request
*** or simply open an issue with the tag "enhancement".
*** Don't forget to give the project a star!
*** Thanks again! Now go create something AMAZING! :D
-->



<!-- PROJECT SHIELDS -->
<!--
*** I'm using markdown "reference style" links for readability.
*** Reference links are enclosed in brackets [ ] instead of parentheses ( ).
*** See the bottom of this document for the declaration of the reference variables
*** for contributors-url, forks-url, etc. This is an optional, concise syntax you may use.
*** https://www.markdownguide.org/basic-syntax/#reference-style-links
-->




<br />
<div align="center">


<h3 align="center">Gait Biometric Dashboard</h3>

  <p align="center">
    A Visualization & Labelling System for Large Scale Analysis of Gait Biometrics
    <br />
    <br />
  </p>
</div>



<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#before-you-begin">Before you begin</a></li>
        <li><a href="#important-note-about-dataroot">Important note about DATAROOT</a></li>
        <li><a href="#normal-startup-after-initial-setup">Normal startup after initial setup</a></li>
        <li><a href="#troubleshooting">Troubleshooting</a></li>
        <li><a href="#quick-summary">Quick summary</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>



<!-- ABOUT THE PROJECT -->
<!--
Here's a blank template to get started. To avoid retyping too much info, do a search and replace with your text editor for the following: `aharris01`, `BiometricGaitDashboard`, `twitter_handle`, `linkedin_username`, `email_client`, `email`, `Gait Biometric Dashboard`, `A Visualization & Labelling System for Large Scale Analysis of Gait Biometrics`, `project_license`
-->
## About The Project

The Health Technologies Lab (HTL) at the University of New Brunswick (UNB) is conducting research based on footsteps collected from pressure tiles installed at a high-security office complex in Fredericton, NB. This dataset of **real-world, noisy data** consists of **200,000+ high-resolution footsteps**, taking up roughly **73 TB** of storage space.

Currently, processing this data for research purposes is manual and time-consuming. This dashboard was created to allow researchers to explore footsteps data in a more time-efficient manner.

This dashboard provides a closer look at locally available footstep data files. Users can explore a summarized view of data, or inspect and modify individual footsteps.

<p align="right">(<a href="#readme-top">back to top</a>)</p>



### Built With

[![Dash][Dash.com]][Dash-url]

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- GETTING STARTED -->
## Getting Started

Follow these instructions to get this dashboard up and running on your machine.

### What you will receive
- A copy of the application repository
- A data subset folder named `data`

### Before you begin
- Install Python 3.11 on your machine
- On Windows, make sure **Add Python to PATH** is checked during installation

### 1. Verify Python is installed
- Open a terminal
- Run:

```bash
python --version
```

- Confirm that Python is available in the terminal

### 2. Place the project files on your machine
- Put the repository in a convenient folder, for example:

```text
C:\UAT\gait-dashboard
```

- Put the provided `data` folder somewhere on your machine, for example:

```text
C:\UAT\data
```

### 3. Confirm the data folder structure
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

### 4. Open a terminal in the repository folder
- Example:

```bash
cd C:\UAT\gait-dashboard
```

### 5. Create a virtual environment
- Run:

```bash
python -m venv .venv
```

### 6. Activate the virtual environment
- On Windows Command Prompt, run:

```bash
.venv\Scripts\activate
```

- On Windows PowerShell, run:

```powershell
.venv\Scripts\Activate.ps1
```

### 7. Install the required packages
- Run:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 8. Configure the `.env` file
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

### Important note about `DATAROOT`
- `DATAROOT` must point to the `data` folder itself
- It must not point to:
  - the parent folder above `data`
  - an individual participant folder inside `data`

### 9. Delete `local.db` before the first run
- In the repository folder, delete:

```text
local.db
```

- Do not delete:

```text
manifest.db
```

- This is a one-time first-run step so the local database can rebuild correctly on the participant’s machine

### 10. Start the application
- From the repository folder, run:

```bash
python main.py
```

### 11. Open the dashboard
- Once the application starts, open this address in a web browser:

```text
http://127.0.0.1:8050
```

### Normal startup after initial setup
- After the one-time setup is complete, starting the app should be as simple as:

```bash
cd C:\UAT\gait-dashboard
.venv\Scripts\activate
python main.py
```

### Troubleshooting
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

### Quick summary
- Put the repo on your machine
- Put the provided `data` folder on your machine
- Set `DATAROOT` in `.env` to the path of the `data` folder
- Delete `local.db` once
- Run:

```bash
python main.py
```


<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- USAGE EXAMPLES -->
## Usage

TODO: give examples of functionality with screenshots

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- CONTACT -->
## Contact

Project Link: [https://github.com/aharris01/BiometricGaitDashboard](https://github.com/aharris01/BiometricGaitDashboard)

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- ACKNOWLEDGMENTS -->
## Acknowledgments

* Dr. Aaron Tabor[]()
* Dr. Erik Scheme, UNB Health Technologies Lab[]()
* Dr. Shivam Saxena[]()

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[product-screenshot]: images/screenshot.png
<!-- Shields.io badges. You can a comprehensive list with many more badges at: https://github.com/inttter/md-badges -->
[Dash.com]: https://img.shields.io/badge/Dash-7A76FF?style=for-the-badge&logo=plotly&logoColor=white
[Dash-url]: https://dash.plotly.com


