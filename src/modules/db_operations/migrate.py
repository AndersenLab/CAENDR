from flask_migrate import Migrate, migrate, upgrade
from functools import wraps

from caendr.services.logger import logger



def migrate_wrapper(f):
  @wraps(f)
  def inner(app, db, *args, **kwargs):

    # Ensure Flask_Migrate is using the provided app & database
    migrate = Migrate()
    migrate.init_app(app, db)

    # Call the wrapped function
    return f(app, db, *args, **kwargs)

  return inner


@migrate_wrapper
def upgrade_database(app, db):
  '''
    Upgrade the database to the most recent revision.
  '''
  logger.debug(f'Upgrading database')
  upgrade()


@migrate_wrapper
def migrate_and_upgrade_database(app, db, message: str = None):
  '''
    Create a new revision and upgrade the database.
  '''
  logger.debug(f'Migrating database: "{message}"')
  migrate(message=message)
  upgrade()
