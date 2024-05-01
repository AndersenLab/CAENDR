import yaml
import csv

from flask      import render_template, Blueprint, redirect, url_for, request, flash, jsonify
from extensions import cache
from config     import config

from caendr.models.error           import EnvVarError, FileUploadError
from caendr.models.datastore       import Species
from caendr.services.cloud.storage import get_blob
from caendr.services.logger        import logger
from caendr.services.validate      import validate_file, StrainValidator, NumberValidator
from caendr.utils.local_files      import LocalUploadFile
from base.utils.auth               import jwt_required, get_current_user
from base.utils.trait              import add_trait
from base.forms                    import TraitSubmissionForm
from constants                     import TOOL_INPUT_DATA_VALID_FILE_EXTENSIONS



data_bp = Blueprint(
  'data', __name__, template_folder='templates'
)


#
# Landing Page
#
@data_bp.route('/')
@cache.memoize(60*60)
def data():
  return redirect(url_for('data_releases.data_releases'))


#
# Download Data
#
@data_bp.route('/download')
@cache.memoize(60*60)
def download():
  title = 'Download Data'
  disable_parent_breadcrumb = True
  return render_template('data/download.html', **locals())


#
# Protocols
#
@data_bp.route("/protocols")
@cache.memoize(60*60)
def protocols():

    # Get location of YAML file in GCP
    MODULE_SITE_BUCKET_ASSETS_NAME = config.get('MODULE_SITE_BUCKET_ASSETS_NAME')
    if not MODULE_SITE_BUCKET_ASSETS_NAME:
      raise EnvVarError('MODULE_SITE_BUCKET_ASSETS_NAME')

    # Download the YAML file as a string
    blob = get_blob(MODULE_SITE_BUCKET_ASSETS_NAME, 'protocols/protocols.yaml')
    content = blob.download_as_text()

    # Initialize params and render HTML page
    params = {
      'title': "Protocols",
      'disable_parent_breadcrumb': True,
      'protocols': yaml.safe_load(content),
    }
    return render_template('data/protocols.html', **params)


#
# Submit Trait
#
@data_bp.route('/trait/start-submit')
@jwt_required()
def submit_trait_start():
  """ Submit Trait start page """
  return render_template('data/submit-trait-start.html', **{
    'title': 'Submit Trait',
    'disable_parent_breadcrumb': True
  })

#
# Submit Trait Form
#
@data_bp.route('/trait/create', methods=['GET', 'POST'])
@jwt_required()
def submit_trait_form():
  """ Trait Submission Form """
  form = TraitSubmissionForm()
  user = get_current_user()

  if hasattr(user, 'username') and not form.username.data:
    form.username.data = user.username

  # Handle form submission
  if request.method == 'POST':
    form = TraitSubmissionForm(request.form)
    form.file.data = request.files.get('file')

    # Validate form fields
    if not form.validate_on_submit():
      flash('Please fill out all required fields.', 'warning')
    
    else:
      # Add the trait to the database
      resp, code = add_trait(form, user)
      if code != 200:
        flash(resp['message'], 'danger')
      else:
        flash('Trait submitted successfully.', 'success')
        return redirect(url_for('data.submit_trait_start'))

  return render_template('data/submit-trait-form.html', **{
    # Page Info
    'title': 'Phenotype Database Trait Submission',
    'tool_alt_parent_breadcrumb': {"title": "Submit Trait", "url": url_for('data.submit_trait_start')},

    # Data
    'form': form,
  })

#
# File Upload
#
@data_bp.route('/trait/parse-file', methods=['POST'])
@jwt_required()
def parse_trait_file():
  """ Parse the trait file and return the data """
  try:
    with LocalUploadFile(request.files.get('file'), valid_file_extensions=TOOL_INPUT_DATA_VALID_FILE_EXTENSIONS) as file:
      # Validate the file
      try:
        species = Species.from_name(request.form.get('species'))
        validate_file(file, [
                              StrainValidator( 'strain', species=species, force_unique=True, force_unique_msgs={} ),
                              NumberValidator( None, accept_float=True, accept_na=True ),
                            ])
      except Exception as ex:
        return jsonify({ 'message': ex.msg }), 500
      
      # Parse the file
      with open(file) as f:
        file_content = []
        for idx, row in enumerate( csv.reader(f, delimiter='\t') ):
          file_content.append({'col_1': row[0], 'col_2': row[1]})
        return jsonify(file_content), 200
      
  except FileUploadError as ex:
    return jsonify({ 'message': ex.description }), ex.code
  
  except Exception as ex:
    logger.error(f'Failed to parse the file: {ex}')
    return jsonify({ 'message': 'Failed to parse the file. Please try again later.' }), 500

