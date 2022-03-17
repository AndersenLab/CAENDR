from dotenv import load_dotenv
from application import create_app
from caendr.utils import monitor

dotenv_file = '.env'
load_dotenv(dotenv_file)

monitor.init_sentry("site")

# Initialize application
app = create_app()
