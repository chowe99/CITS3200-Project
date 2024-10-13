# CITS3200-Project

**Prerequisites:**

- Docker ([Installation Guide](https://docs.docker.com/get-docker/))
- Docker Compose ([Installation Guide](https://docs.docker.com/compose/install/))


## Running the App
Use the start.sh script to mount the NAS and start the Docker container.

### Mac Users

```bash
./start.sh "[IRDS_DRIVE_PATH]"
```
**Parameters:**

- `IRDS_DRIVE_PATH`: Optional argument to specify a custom SMB share path.
    - **Default:** smb://drive.irds.uwa.edu.au/RES-ENG-CITS3200-P000735

**Examples:**

- Default NAS Path:

```bash
./start.sh
```
**Custom NAS Path:**

```bash
./start.sh "smb://drive.irds.uwa.edu.au/<YOUR_SHARE_HERE>"
```

### Windows and Linux Users

**Environment Variables:**

To securely handle your SMB credentials, you need to set the following environment variables in your shell configuration file (`.bashrc`, `.zshrc`, etc.):

```bash
export SMB_USERNAME="your_IRDS_username"
export SMB_PASSWORD="your_IRDS_password"
export REAL_NAS=true  # Set to 'false' to use simulated NAS in testing environments
```

After adding the above lines, reload your shell configuration:

```bash
source ~/.bashrc  # or source ~/.zshrc
```

Ensure that SMB\_USERNAME and SMB\_PASSWORD are set in your environment variables as described above. Then run:

```bash
./start.sh "[IRDS_DRIVE_PATH]"
```

## Stopping the App

Press Ctrl+C in the terminal where start.sh is running to stop the Docker container and perform cleanup.
