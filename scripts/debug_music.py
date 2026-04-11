import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

import backend.spotify_api as spotify_api
from backend.auth_spotify import TOKEN_STORE
import requests
from config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET
import traceback

def run():
    print("Testing locally...")
    # I need a valid token. Since I don't have one, I can't test. I need to make a request to the local API that triggers it so it prints to MY terminal.
    # But wait, fast API logs are in the `make up` terminal. 
    # I can just kill `make up` and run it myself in the background and pipe to a file, then curl, then read the file!
    pass

if __name__ == '__main__':
    run()
