import os
from clerk_backend_api import Clerk
from dotenv import load_dotenv

# Ensure environment variables are loaded
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
env_path = os.path.join(BASE_DIR, 'env', '.env')
load_dotenv(env_path)

CLERK_SECRET_KEY = os.getenv('CLERK_SECRET_KEY', '')

# Initialize the Clerk backend client
# This client will be used to verify session tokens in the backend
clerk_client = Clerk(bearer_auth=CLERK_SECRET_KEY)
