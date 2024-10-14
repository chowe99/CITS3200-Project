import sys
import os

# Specify the folder path
folder_path = '//drive.irds.uwa.edu.au/RES-ENG-CITS3200-P000735'

# List all files in the specified folder
try:
    with os.scandir(folder_path) as entries:
        for entry in entries:
            if entry.is_file():
                print(entry.name)
except FileNotFoundError:
    print(f"The folder '{folder_path}' does not exist.")

print(sys.prefix)