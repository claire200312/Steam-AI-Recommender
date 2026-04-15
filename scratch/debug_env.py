import os
from dotenv import load_dotenv

# Path logic from main.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(BASE_DIR, "../.env") # Note: main.py uses ../../.env because it's in scene/backend
# Wait, if main.py is in scene/backend, then ../../.env is the root.
# My script is in scratch.
root_env = os.path.join(os.path.dirname(BASE_DIR), ".env")

load_dotenv(root_env)
key = os.getenv("OPENAI_API_KEY")
if key:
    print(f"Key Found. Ends with: {key[-4:]}")
else:
    print("Key NOT found in environment.")
