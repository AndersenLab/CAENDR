from logzero import logger
from flask import Blueprint, render_template, request, redirect, url_for

from base.utils.auth import get_jwt, jwt_required, get_current_user
from base.forms import FileUploadForm

from caendr.services.nemascan_mapping import create_new_mapping, get_mapping, get_user_mappings
from caendr.services.cloud.storage import generate_blob_url


mapping_bp = Blueprint('mapping',
                      __name__)


@mapping_bp.route('/mapping/perform-mapping/', methods=['GET'])
@jwt_required()
def mapping():
  """
      This is the mapping submission page.
  """
  title = 'Perform Mapping'
  jwt_csrf_token = (get_jwt() or {}).get("csrf")
  form = FileUploadForm()
  # TODO: change
  nemascan_container_url = 'https://github.com/AndersenLab/dockerfile/tree/nemarun/nemarun'
  nemascan_github_url = 'https://github.com/AndersenLab/NemaScan'
  return render_template('tools/mapping/mapping.html', **locals())


@mapping_bp.route('/mapping/upload', methods = ['POST'])
@jwt_required()
def submit_mapping_request():
  form = FileUploadForm(request.form)
  user = get_current_user()
  if not form.validate_on_submit():
    flash("You must include a description of your data and a TSV file to upload", "error")
    return redirect(url_for('mapping.mapping'))
  
  props = {'label': request.form.get('label'),
          'username': user.name,
          'file': request.files['file'],
          'status': ''}
  
  m = create_new_mapping(**props)
  if m.status == 'DUPLICATE' or m.status == 'COMPLETE':
    flash('It looks like that data has already been uploaded - You will be redirected to the saved results', 'danger')
  return redirect(url_for('mapping.mapping_report', id=m.id))


@mapping_bp.route('/mapping/report/all', methods=['GET', 'POST'])
@jwt_required()
def mapping_report_list():
  title = 'Genetic Mapping'
  subtitle = 'Report List'
  user = get_current_user()
  username = user.name
  mappings = get_user_mappings(username)

  return render_template('tools/mapping/list.html', **locals())


@mapping_bp.route('/mapping/report/<id>', methods=['GET'])
@jwt_required()
def mapping_report(id):
  title = 'Genetic Mapping Report'
  user = get_current_user()
  mapping = get_mapping(id)
  data_url = generate_blob_url(mapping.get_bucket_name(), mapping.get_data_blob_path())
  
  return render_template('tools/mapping/report.html', **locals())


@mapping_bp.route('/mapping/report/<id>/results/', methods=['GET'])
@jwt_required()
def mapping_results(id):
  title = 'Genetic Mapping Result Files'
  user = get_current_user()

  return render_template('tools/mapping/result_files.html', **locals())

