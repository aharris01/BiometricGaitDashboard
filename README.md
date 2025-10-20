## Steps to Access the Cyber Center Dataset
### 1. Connect to the Server (use UNB VPN)
- Connect to UNB VPN first.
- Open a terminal and run
  ```bash
  ssh <username>@lambda.int.unb.ca
  ```
- Enter the temporary password
### 2. Change Password
- run this command to change password.
  ```bash
  passwd
  ```
- Enter the old password once, then type new password twice.
### 3. Dataset Access
- see dataset contents:
  ```bash
  ls /home/cc-data/cc
  ```
- move into the data folder:
  ```bash
  cd /home/cc-data/cc
  ```
- inspect file details:
  ```bash
  ls -lh
  ```
- preview a text file:
  ```bash
  head filename.txt
  ```
