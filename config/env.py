from dotenv import load_dotenv
import os

load_dotenv()  # auto-loads .env from project root

def env(key, default=None):
    return os.getenv(key, default)
