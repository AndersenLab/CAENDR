from application import create_app

from caendr.services.logger import logger
from caendr.utils import monitor
from caendr.utils.env import load_env


dotenv_file = '.env'
load_env(dotenv_file)

monitor.init_sentry("site")

# Initialize application
app = create_app()
