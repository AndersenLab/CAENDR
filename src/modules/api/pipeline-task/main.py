import os
from flask import Flask
from dotenv import load_dotenv

load_dotenv('.env')
load_dotenv('module.env')

from caendr.utils import monitor
from caendr.blueprints import api_error_handler_bp
from routes.task import task_handler_bp
from routes.base import base_bp

ENV = os.environ.get('FLASK_ENV', 'development')
PORT = os.environ.get('PORT', 8080)

monitor.init_sentry("pipeline-task")

app = Flask(__name__)
app.register_blueprint(base_bp)
app.register_blueprint(api_error_handler_bp)
app.register_blueprint(task_handler_bp, url_prefix="/task")

if __name__ == "__main__":
  app.run(host="localhost", port=PORT, debug=True)


