import os
from flask import Flask
from dotenv import load_dotenv

from routes.error_handlers import error_handler_bp
from routes.task import task_handler_bp

ENV = os.environ.get('FLASK_ENV', 'development')
PORT = os.environ.get('PORT', 8080)

dotenv_file = '.env'
load_dotenv(dotenv_file)

app = Flask(__name__)
app.register_blueprint(error_handler_bp)
app.register_blueprint(task_handler_bp, url_prefix="/task")

if __name__ == "__main__":
  app.run(host="localhost", port=PORT, debug=True)


