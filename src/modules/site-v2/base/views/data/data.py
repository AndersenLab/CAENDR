import yaml
import csv
from datetime import datetime

from flask      import render_template, Blueprint, redirect, url_for, request, flash, jsonify, abort
from extensions import cache
from config     import config

from caendr.models.error           import EnvVarError, FileUploadError
from caendr.models.datastore       import Species, TraitFile
from caendr.api.phenotype          import get_phenotype_values_for_trait
from caendr.services.cloud.storage import get_blob
from caendr.services.logger        import logger
from caendr.services.validate      import validate_file, StrainValidator, NumberValidator
from caendr.utils.local_files      import LocalUploadFile
from base.utils.auth               import jwt_required, get_current_user, user_is_admin
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
    'new_submission': True,

    # Data
    'form': form,
    'phenotype_values': None,
  })


@data_bp.route('/trait/<id>')
@jwt_required()
def trait(id):
  """ Trait Page"""
  trait_ds = TraitFile.get_ds(id)
  trait_name = ' '.join(trait_ds.display_name)
  phenotype_values = get_phenotype_values_for_trait(id)
  return render_template('data/trait.html', **{
    # Page Info}
    'title': f'Trait {trait_name}',
    'tool_alt_parent_breadcrumb': {"title": "Traits", "url": '/'}, # TODO: Update this to the correct URL

    # Data
    'trait_name': trait_name,
    'trait': trait_ds.serialize(),
    'file_content': phenotype_values,
  })

@data_bp.route('/trait/<id>/edit', methods=['GET', 'PUT'])
@jwt_required()
def edit_trait(id):
  """ Edit Trait Page"""
  user = get_current_user()
  trait_ds = TraitFile.get_ds(id).serialize()
  if user.username != trait_ds['username'] and not user_is_admin():
    return abort(401)

  form_data = {
    'species':              trait_ds.get('species'),
    'trait_name_user':      trait_ds.get('trait_name_caendr') if trait_ds['from_caendr'] else trait_ds.get('trait_name_user'),
    'trait_name_display_1': trait_ds.get('trait_name_display_1'),
    'trait_name_display_2': trait_ds.get('trait_name_display_2'),
    'trait_name_display_3': trait_ds.get('trait_name_display_3'),
    'description_short':    trait_ds.get('description_short'),
    'description_long':     trait_ds.get('description_long'),
    'unit':                 trait_ds.get('unit'),
    'tags':                 trait_ds.get('tags'),
    'username':             trait_ds.get('username'),
    'institution':          trait_ds.get('institution'),
    'source_lab':           trait_ds.get('source_lab'),
    'protocols':            trait_ds.get('protocols'),
    'publication':          trait_ds.get('publication')
  }
  form = TraitSubmissionForm(data=form_data)
  return render_template('data/submit-trait-form.html', **{
    # Page Info
    'title': trait_ds['trait_name_display_1'],
    # 'tool_alt_parent_breadcrumb': {"title": "Submit Trait", "url": url_for('data.submit_trait_start')},
    'new_submission': False,

    # Data
    'form': form,
    'phenotype_values': [ v.to_json() for v in get_phenotype_values_for_trait(id) ],
    'file': {
      'name': trait_ds['filename'],
      'created_on': datetime.strftime(trait_ds['created_on'], "%Y-%m-%d"),
    }
  })


#
# File Upload
#
@data_bp.route('/trait/parse-file', methods=['POST'])
@jwt_required()
def validate_and_parse_trait_file():
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
      file_content = parse_trait_file(file)
      return jsonify(file_content), 200
      
  except FileUploadError as ex:
    return jsonify({ 'message': ex.description }), ex.code
  
  except Exception as ex:
    logger.error(f'Failed to parse the file: {ex}')
    return jsonify({ 'message': 'Failed to parse the file. Please try again later.' }), 500


def parse_trait_file(file):
  """ Parse a trait file into a list of dictionaries """
  with open(file) as f:
    file_content = []
    for idx, row in enumerate( csv.reader(f, delimiter='\t') ):
      file_content.append({'col_1': row[0], 'col_2': row[1]})
    return file_content