# CITS3200-Project

**Prerequisites:**

- Docker (Either link to install guide, write one here, or automate start.sh script to install it)


**Running the app:**

run `./start.sh [IRDS_DRIVE_PATH]`

example: `./start.sh "smb://drive.irds.uwa.edu.au/RES-ENG-CITS3200-P000735"`

- Windows users:

    `SMB\_USERNAME="your\_IRDS\_username" SMB\_PASSWORD="your\_IRDS\_password" ./start.sh [IRDS_DRIVE_PATH]`

The database file should be named "soil\_test\_results.db" and located at the root of the IRDS directory.

