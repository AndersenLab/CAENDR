from flask_alembic import Alembic

from caendr.services.logger import logger



def upgrade_database(app, alembic: Alembic):
  '''
    Upgrade the database to the most recent revision.
  '''
  logger.debug(f'Upgrading database to latest revision: { alembic.heads()[0] }')
  alembic.upgrade()


def migrate_and_upgrade_database(app, alembic: Alembic, message: str = None):
  '''
    Create a new revision and upgrade the database.
  '''
  logger.debug(f'Migrating database: "{message}"')
  alembic.revision(message)
  alembic.upgrade()
