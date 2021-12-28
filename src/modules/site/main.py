from dotenv import load_dotenv
from application import create_app

dotenv_file = '.env'
load_dotenv(dotenv_file)

# Initialize application
app = create_app()
