from caendr.services.logger import logger
from flask import Blueprint, render_template, request, redirect, url_for, flash
import bleach
from flask import jsonify


from base.utils.auth import get_jwt, jwt_required, admin_required, get_current_user
from base.forms import FileUploadForm

from caendr.services.nemascan_mapping import create_new_mapping, get_mapping, get_all_mappings, get_user_mappings
from caendr.services.cloud.storage import get_blob, generate_blob_url, get_blob_list
from caendr.models.error import CachedDataError, DuplicateDataError
from caendr.models.species import SPECIES_LIST


mapping_bp = Blueprint('mapping',
                      __name__)


@mapping_bp.route('/mapping/perform-mapping/', methods=['GET'])
@jwt_required()
def mapping():
  """
      This is the mapping submission page.
  """
  return render_template('tools/mapping/mapping.html', **{

    # Page info
    'title': 'Perform Mapping',

    # Form info
    'jwt_csrf_token': (get_jwt() or {}).get("csrf"),
    'form': FileUploadForm(),

    # TODO: change
    'nemascan_container_url': 'https://github.com/AndersenLab/dockerfile/tree/nemarun/nemarun',
    'nemascan_github_url':    'https://github.com/AndersenLab/NemaScan',

    # Species list
    'species_list': SPECIES_LIST,
    'species_fields': [
      'name', 'short_name', 'project_num', 'wb_ver', 'latest_release',
    ],
  })


@mapping_bp.route('/mapping/upload', methods = ['POST'])
@jwt_required()
def submit_mapping_request():
  form = FileUploadForm(request.form)
  user = get_current_user()

  # Validate form
  if not form.validate_on_submit():
    flash("You must include a description of your data and a TSV file to upload", "error")
    return redirect(url_for('mapping.mapping'))

  # Read fields from form
  label   = bleach.clean(request.form.get('label'))
  species = bleach.clean(request.form.get('species'))
  props = {
    'username': user.name,
    'email':    user.email,
    'label':    label,
    'file':     request.files['file'],
    'species':  species,
  }

  try:
    logger.warn("Check Duplicates is DISABLED !!!")
    m = create_new_mapping(**props, check_duplicates=True)
    return redirect(url_for('mapping.mapping_report', id=m.id))

  except DuplicateDataError as ex:
    flash('It looks like you submitted that data already - redirecting to your list of Mapping Reports', 'danger')
    return redirect(url_for('mapping.mapping_user_reports'))

  except CachedDataError as ex:
    flash('It looks like that data has already been submitted - redirecting to the saved results', 'danger')
    return redirect(url_for('mapping.mapping_report', id=ex.description))

  except Exception as ex:
    logger.error(ex.description)
    flash(f"Unable to submit your request: \"{ex.description}\"", 'danger')
    return redirect(url_for('mapping.mapping'))


@mapping_bp.route('/mapping/reports/all', methods=['GET', 'POST'])
@admin_required()
def mapping_all_reports():
  title = 'All Genetic Mappings'
  subtitle = 'Report List'
  user = get_current_user()
  mappings = get_all_mappings()
  return render_template('tools/mapping/list-all.html', **locals())


@mapping_bp.route('/mapping/reports', methods=['GET', 'POST'])
@jwt_required()
def mapping_user_reports():
  title = 'My Genetic Mappings'
  subtitle = 'Report List'
  user = get_current_user()
  mappings = get_user_mappings(user.name)
  return render_template('tools/mapping/list-user.html', **locals())


@mapping_bp.route('/mapping/report/<id>', methods=['GET'])
@jwt_required()
def mapping_report(id):
  title = 'Genetic Mapping Report'
  user = get_current_user()
  mapping = get_mapping(id)
  subtitle = mapping.label +': ' + mapping.trait
  fluid_container = True
  data_url = generate_blob_url(mapping.get_bucket_name(), mapping.get_data_blob_path())
  # if hasattr(mapping, 'mapping_report_url'):
  if hasattr(mapping, 'report_path'):
    report_url = generate_blob_url(mapping.get_bucket_name(), mapping.report_path)
  else:
    report_url = None

  report_status_url = url_for("mapping.mapping_report_status", id=id)

  return render_template('tools/mapping/report.html', **locals())

@mapping_bp.route('/mapping/report/<id>/fullscreen', methods=['GET'])
@jwt_required()
def mapping_report_fullscreen(id):
  title = 'Genetic Mapping Report'
  user = get_current_user()
  mapping = get_mapping(id)
  subtitle = mapping.label +': ' + mapping.trait
  fluid_container = True
  data_url = generate_blob_url(mapping.get_bucket_name(), mapping.get_data_blob_path())
  # if hasattr(mapping, 'mapping_report_url'):
  if hasattr(mapping, 'report_path'):
    blob = get_blob(mapping.get_bucket_name(), mapping.report_path)
    report_contents = blob.download_as_text()
  else:
    report_contents = None

  return report_contents

@mapping_bp.route('/mapping/report/<id>/status', methods=['GET'])
@jwt_required()
def mapping_report_status(id):
  mapping = get_mapping(id)
  data_url = generate_blob_url(mapping.get_bucket_name(), mapping.get_data_blob_path())
  if hasattr(mapping, 'mapping_report_url'):
    report_url = generate_blob_url(mapping.get_bucket_name(), mapping.report_path)
  else:
    report_url = None

  payload = {
    'done': True if report_url else False,
    'report_url': report_url if report_url else "https://www.google.com"
  }
  return jsonify(payload)


@mapping_bp.route('/mapping/report/<id>/results/', methods=['GET'])
@jwt_required()
def mapping_results(id):
  title = 'Genetic Mapping Result Files'
  user = get_current_user()
  mapping = get_mapping(id)
  subtitle = mapping.label + ': ' + mapping.trait
  blobs = get_blob_list(mapping.get_bucket_name(), mapping.get_result_path())
  file_list = []
  for blob in blobs:
    file_list.append({
      "name": blob.name.rsplit('/', 2)[1] + '/' + blob.name.rsplit('/', 2)[2],
      "url": blob.public_url
    })
    
  return render_template('tools/mapping/result_files.html', **locals())




  data_blob = RESULT_BLOB_PATH.format(data_hash=ns.data_hash)
  blobs = list_files(data_blob)
  file_list = []
  for blob in blobs:
    file_list.append({
      "name": blob.name.rsplit('/', 2)[1] + '/' + blob.name.rsplit('/', 2)[2],
      "url": blob.public_url
    })
    
  return render_template('mapping_result_files.html', **locals())
