import json
import os
# from attr import has
from caendr.services.cloud.postgresql import health_database_status
from caendr.services.logger import logger
from flask import Blueprint, render_template, url_for, request, redirect, flash, Markup

from base.utils.auth import admin_required, get_jwt, get_jwt_identity, get_current_user
from base.forms import AdminCreateDatabaseOperationForm

from caendr.services.database_operation import get_all_db_ops, get_etl_op, get_db_op_form_options
from caendr.services.cloud.storage import BlobURISchema, generate_blob_uri

from caendr.models.error        import PreflightCheckError
from caendr.models.job_pipeline import DatabaseOperationPipeline

from google.cloud import storage


ETL_LOGS_BUCKET_NAME = os.getenv('ETL_LOGS_BUCKET_NAME')

storage_client = storage.Client()


admin_etl_op_bp = Blueprint(
  'admin_etl_op', __name__, template_folder='templates'
)



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

  # Check db status
  status, message = health_database_status()
  logger.debug(f"DB Status is {status} {message}")
  logger.debug("ETL Stats loading...")

  return render_template('admin/etl/stats.html', **{
    'title': 'ETL Stats',
    'alt_parent_breadcrumb': {"title": "Admin", "url": url_for('admin.admin')},
  })



@admin_etl_op_bp.route('/<id>/view', methods=["GET"])
@admin_required()
def view_op(id):
  title = "View ETL Operation"    
  op = get_etl_op(id)

  log_contents = ""
  uri = op.get('logs', None)
  if uri is not None:
    bucket = storage_client.get_bucket(ETL_LOGS_BUCKET_NAME)
    filepath = uri.replace( generate_blob_uri(ETL_LOGS_BUCKET_NAME, schema=BlobURISchema.GS), '' )
    blob = bucket.get_blob(filepath)
    if blob is not None:
      log_contents = blob.download_as_string().decode('utf8')
      log_contents.replace("\n", "<br/>")

  format = request.args.get('format')
  if format == 'json':
    return json.dumps(op, indent=4, sort_keys=True, default=str)

  return render_template('admin/etl/view.html', **locals())



@admin_etl_op_bp.route('/create', methods=["GET", "POST"])
@admin_required()
def create_op():

  # Set up the form
  form = AdminCreateDatabaseOperationForm(request.form)
  form.db_op.choices = get_db_op_form_options()

  ## GET Request ##
  # Show the form page
  if not (request.method == 'POST' and form.validate_on_submit()):
    return render_template('admin/etl/create.html', **{
      'title': 'Execute a Database Operation',
      'alt_parent_breadcrumb': { "title": "Admin/ETL", "url": url_for('admin_etl_op.admin_etl_op') },

      # Form
      'jwt_csrf_token': (get_jwt() or {}).get("csrf"),
      'form': form,
    })

  ## POST Request ##
  # Submit the form

  user = get_current_user()

  # Try parsing the form into a job handler & submitting the job
  try:
    job = DatabaseOperationPipeline.create(user, form.data)
    job.schedule()

  # Preflight check error: one or more required files are missing from cloud storage
  except PreflightCheckError as ex:
    files_txt = ''.join([ f'<br />{filename}' for filename in ex.missing_files ])
    flash(Markup(f'Could not submit job. Missing the following files:{files_txt}'), category='danger')
    return redirect(request.url)

  # Redirect back to the full list
  return redirect(url_for("admin_etl_op.admin_etl_op"), code=302)
