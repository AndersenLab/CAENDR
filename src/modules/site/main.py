from dotenv import load_dotenv
from application import create_app
import monitor

dotenv_file = '.env'
load_dotenv(dotenv_file)

monitor.init_sentry()

# Initialize application
app = create_app()
