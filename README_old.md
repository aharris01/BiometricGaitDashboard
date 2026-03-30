## Configuration
Copy the contents of .env.example into a new .env file

#### Config Contents
 - DATAROOT: The root directory where your local copy of the dataset resides. The participant folders must be the next folders in the hierarchy. If not set, defaults to the root directory where the program is run from.

 ## Running
To run the program, run `python main.py` from the root directory of the cloned repository. In the console you will see two Flask servers running, one for the Dash frontend and the other for the business logic Backend. To use the dashboard, open a browser and go to [127.0.0.1:8050](127.0.0.1:8050).
<br>

To stop the program, press CTRL+C to quit