import os
key = os.getenv("OPENAI_API_KEY", "NOT_SET")
print(f"System Env Key Ends: {key[-4:] if key != 'NOT_SET' else 'NOT_SET'}")
