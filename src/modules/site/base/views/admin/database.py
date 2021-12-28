from flask import Blueprint, render_template, url_for, request, redirect

from base.utils.auth import admin_required, get_jwt, get_jwt_identity
from base.forms import AdminCreateDatabaseOperationForm

from caendr.services.database_operation import get_all_db_ops, create_new_db_op, get_db_op_form_options

admin_db_op_bp = Blueprint('admin_db_op',
                            __name__,
                            template_folder='templates')


@admin_db_op_bp.route('', methods=["GET"])
@admin_required()
def admin_db_op():
  alt_parent_breadcrumb = {"title": "Admin", "url": url_for('admin.admin')}
  title = 'Database Operations'
  database_operations = get_all_db_ops(placeholder=False)
  return render_template('admin/database/list.html', **locals())


@admin_db_op_bp.route('/create', methods=["GET", "POST"])
@admin_required()
def create_op():
  title = 'Execute a Database Operation'
  alt_parent_breadcrumb = {"title": "Admin/Database Operations", "url": url_for('admin_db_op.admin_db_op')}

  jwt_csrf_token = (get_jwt() or {}).get("csrf")
  form = AdminCreateDatabaseOperationForm(request.form)
  form.db_op.choices = get_db_op_form_options()
  if request.method == 'POST' and form.validate_on_submit():
    db_op = request.form.get('db_op')
    wormbase_version = request.form.get('wormbase_version')
    sva_version = request.form.get('sva_version')
    note = request.form.get('note')
    username = get_jwt_identity()
    args = {'WORMBASE_VERSION': f'WS{wormbase_version}' if wormbase_version else '',
            'STRAIN_VARIANT_ANNOTATION_VERSION': sva_version}
    
    create_new_db_op(db_op, username, args=args, note=note)
    return redirect(url_for("admin_db_op.admin_db_op"), code=302)

    
  return render_template('admin/database/create.html', **locals())