from main import app
from caendr.models.sql import Homolog
from caendr.services.cloud.postgresql import db
from main import app

def create_schema():
    with app.app_context():
        try:
            db.init_app(app)
            Homolog.metadata.create_all(db.engine)
            db.session.commit()
        except Exception as e:
            print(e)

if __name__ == "__main__":
    create_schema()