from flask import Blueprint, url_for, abort, request

from caendr.models.sql                  import DbOp, ALL_SQL_TABLES
from caendr.services.cloud.postgresql   import alembic
from caendr.services.database_operation import count_table_rows_safe
from caendr.utils.json                  import jsonify_request


api_database_bp = Blueprint('api_database', __name__)



@api_database_bp.route('', methods=['GET'])
def notifications():
  abort(404)


@api_database_bp.route('/stats', methods=['GET'])
@jsonify_request
def get_all_db_stats():
  '''
    Count the rows in each table, and return all results.
    Returns `None` for any table that threw an error when trying to count the rows.
  '''
  return [ [model.__tablename__, count_table_rows_safe(model)] for model in ALL_SQL_TABLES ]


@api_database_bp.route('/migrations', methods=['GET'])
@jsonify_request
def get_all_db_migrations():
  return [
    [rev.revision, rev.doc, '*' if rev.is_head else ''] for rev in alembic.log()
  ]
