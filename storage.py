import os
import json

DATA_FILES = [
    "study_notes.json",
    "warnings.json",
    "settings.json"
]

def ensure_data_files():
    for filename in DATA_FILES:
        if not os.path.exists(filename):
            with open(filename, "w", encoding="utf-8") as f:
                json.dump({}, f)
