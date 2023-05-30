from flask import Flask,render_template

import os
from logging import Logger
logger = Logger(__name__)

PORT = os.getenv("PORT","8080")
logger.info(f"Listening on port: {PORT}")


app = Flask(__name__,
            static_url_path='', 
            static_folder='web',
            template_folder='web')

@app.route('/')
def index():
    return render_template("index.html")

@app.errorhandler(404)
def not_found(e):
  return render_template("index.html")

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=False, port=PORT)
