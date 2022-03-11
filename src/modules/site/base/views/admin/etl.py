import json
from caendr.services.cloud.postgresql import health_database_status
from logzero import logger
from flask import Blueprint, render_template, url_for, request, redirect

from base.utils.auth import admin_required, get_jwt, get_jwt_identity, get_current_user
from base.forms import AdminCreateDatabaseOperationForm

from caendr.services.database_operation import get_all_db_ops, get_all_db_stats, get_etl_op, create_new_db_op, get_db_op_form_options

admin_etl_op_bp = Blueprint('admin_etl_op',
                            __name__,
                            template_folder='templates')


@admin_etl_op_bp.route('', methods=["GET"])
@admin_required()
def admin_etl_op():
  alt_parent_breadcrumb = {"title": "Admin", "url": url_for('admin.admin')}
  title = 'ETL Operations'
  etl_operations = get_all_db_ops(placeholder=False)
  return render_template('admin/etl/list.html', **locals())


@admin_etl_op_bp.route('/stats', methods=["GET"])
@admin_required()
def admin_etl_stats():
  alt_parent_breadcrumb = {"title": "Admin", "url": url_for('admin.admin')}
  title = 'ETL Stats'
  status, message = health_database_status()
  logger.debug(f"DB Status is {status} {message}")
  logger.debug("ETL Stats loading...")
  stats = get_all_db_stats()
  logger.info(stats)
  return render_template('admin/etl/stats.html', **locals())



@admin_etl_op_bp.route('/<id>/view', methods=["GET"])
@admin_required()
def view_op(id):
  title = "View ETL Operation"    
  op = get_etl_op(id)

  format = request.args.get('format')
  if format == 'json':
    return json.dumps(op, indent=4, sort_keys=True, default=str)

  return render_template('admin/etl/view.html', **locals())

@admin_etl_op_bp.route('/create', methods=["GET", "POST"])
@admin_required()
def create_op():
  title = 'Execute a Database Operation'
  alt_parent_breadcrumb = {"title": "Admin/ETL", "url": url_for('admin_etl_op.admin_etl_op')}

  jwt_csrf_token = (get_jwt() or {}).get("csrf")
  form = AdminCreateDatabaseOperationForm(request.form)
  form.db_op.choices = get_db_op_form_options()
  if request.method == 'POST' and form.validate_on_submit():
    db_op = request.form.get('db_op')
    wormbase_version = request.form.get('wormbase_version')
    sva_version = request.form.get('sva_version')
    note = request.form.get('note')
    username = get_jwt_identity()
    user = get_current_user()
    email = user.email

    args = {'WORMBASE_VERSION': f'WS{wormbase_version}' if wormbase_version else '',
            'STRAIN_VARIANT_ANNOTATION_VERSION': sva_version
            }
    
    create_new_db_op(db_op, username, email, args=args, note=note)
    return redirect(url_for("admin_etl_op.admin_etl_op"), code=302)

    
  return render_template('admin/etl/create.html', **locals())