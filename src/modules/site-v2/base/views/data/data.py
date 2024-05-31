import yaml
import csv
import os
from datetime import datetime

from flask      import render_template, Blueprint, redirect, url_for, request, flash, jsonify, abort, send_file
from extensions import cache
from config     import config

from caendr.api.phenotype          import get_trait_categories
from caendr.models.error           import EnvVarError, FileUploadError
from caendr.models.datastore       import Species, TraitFile
from caendr.models.trait           import Trait
from caendr.api.phenotype          import get_phenotype_values_for_trait
from caendr.services.cloud.storage import get_blob, download_blob_to_file
from caendr.services.logger        import logger
from caendr.services.validate      import validate_file, StrainValidator, NumberValidator
from caendr.utils.local_files      import LocalUploadFile
from caendr.utils.env              import get_env_var
from caendr.utils.data             import get_file_format
from base.utils.auth               import jwt_required, get_current_user, user_is_admin
from base.utils.trait              import add_trait, update_trait_metadata, user_is_trait_owner
from base.utils.view_decorators    import parse_trait
from base.forms                    import TraitSubmissionForm, EmptyForm
from constants                     import TOOL_INPUT_DATA_VALID_FILE_EXTENSIONS

MODULE_DB_OPERATIONS_BUCKET_NAME = get_env_var('MODULE_DB_OPERATIONS_BUCKET_NAME')
UPLOADS_DIR = os.path.join('.', 'uploads')


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
# Trait Library
#


@data_bp.route('/trait/library', methods=['GET'])
@jwt_required()
def my_trait_library():

  # Get the list of unique tags
  try:
    categories = get_trait_categories()

  except Exception as ex:
    logger.error(f'Failed to retrieve the list of traits: {ex}')
    abort(500, description='Failed to retrieve the list of traits')

  return render_template('data/trait-library.html', **{
    # Page info
    'title': 'My Trait Library',

    # Data
    'categories': categories,
    'form': EmptyForm(),
  })



#
# Submit Trait
#
@data_bp.route('/trait/start-submit')
@cache.memoize(60*60)
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
@cache.memoize(60*60)
@jwt_required()
def submit_trait_form():
  """ Trait Submission Form """
  form = TraitSubmissionForm()
  user = get_current_user()

  if hasattr(user, 'email') and not form.email.data:
    form.email.data = user.email

  # Handle form submission
  if request.method == 'POST':
    form = TraitSubmissionForm(request.form)
    form.file.data = request.files.get('file')

    # Validate form fields
    if not form.validate_on_submit():
      flash(f'Please fill out all required fields: {form.errors}', 'warning')
    
    else:
      # Add the trait to the database
      resp, code = add_trait(form, user)
      if code != 200:
        flash(resp['message'], 'danger')
      else:
        flash('Trait submitted successfully.', 'success')
        return redirect(url_for('data.view_trait', trait_id=resp['trait_id']))

  return render_template('data/submit-trait-form.html', **{
    # Page Info
    'title':                      'Phenotype Database Trait Submission',
    'tool_alt_parent_breadcrumb': {"title": "Submit Trait", "url": url_for('data.submit_trait_start')},
    'new_submission':             True,

    # Data
    'form':             form,
    'phenotype_values': None,
  })



#
# View & Edit Trait
#


@data_bp.route('/trait/<string:trait_id>/view',   endpoint='view_trait')
@data_bp.route('/trait/<string:trait_id>/review', endpoint='review_trait')
@cache.memoize(60*60)
@jwt_required()
@parse_trait(validate_owner=True, allow_admin=True)
def trait(trait: Trait):
  """
    View / Review Trait Page
  """

  # Track which endpoint was called
  reviewing = request.endpoint.endswith('review_trait')

  # Validate admin on review endpoint
  if reviewing and not user_is_admin():
    abort(404)

  phenotype_values = get_phenotype_values_for_trait(trait.sql_row.id)
  return render_template('data/trait.html', **{
    # Page Info
    'title': ('Review' if reviewing else 'View') + ' Trait',
    'subtitle': trait.display_name[0],
    'tool_alt_parent_breadcrumb': {"title": "My Trait Library", "url": url_for('data.my_trait_library')},

    # Data
    'trait_name':    ' '.join(trait.display_name),
    'trait':         { **trait.file.serialize(), 'name': trait.file.name },
    'file_content':  phenotype_values,
    'form':          EmptyForm(),
    'user_is_owner': trait.file.belongs_to_user(get_current_user()),
    # 'user_is_owner': user_is_trait_owner(trait.file.serialize(), get_current_user()),

    'reviewing': reviewing,
  })


@data_bp.route('/trait/<string:id>/edit', methods=['GET', 'PUT'])
@cache.memoize(60*60)
@jwt_required()
def edit_trait(id):
  """
    Edit Trait Page
  """
  user = get_current_user()
  trait_ds = TraitFile.get_ds(id).serialize(include_name=True)
  if user_is_trait_owner(trait_ds, user) and not user_is_admin():
    return abort(401)
  
  # Handle Trait Update
  if request.method == 'PUT':
    form = TraitSubmissionForm(request.form)
    form.species.data = trait_ds['species']
    form.email.data = trait_ds['submitter_email']

    # Validate form fields
    if not form.validate_on_submit():
      return jsonify({'message': f'Please fill out all required fields: {form.errors}'}), 500
    
    # Update the trait metadata
    else:
      resp, code = update_trait_metadata(id, form.data)
      if code != 200:
        flash(resp['message'], 'danger')
      else:
        flash(resp['message'], 'success')
        return jsonify( resp ), code

  # Get the endpoint to return to, and validate it creates a legitimate URL
  return_to = request.args.get('return_to', 'view_trait')
  try:
    test_url = url_for(f'data.{return_to}', trait_id=trait_ds['name'])
  except:
    return_to = 'view_trait'

  form_data = {
    'species':              trait_ds.get('species'),
    'trait_name_user':      trait_ds.get('trait_name_caendr') if trait_ds.get('from_caendr') else trait_ds.get('trait_name_user'),
    'trait_name_display_1': trait_ds.get('trait_name_display_1'),
    'trait_name_display_2': trait_ds.get('trait_name_display_2'),
    'trait_name_display_3': trait_ds.get('trait_name_display_3'),
    'description_short':    trait_ds.get('description_short'),
    'description_long':     trait_ds.get('description_long'),
    'unit':                 trait_ds.get('unit'),
    'tags':                 trait_ds.get('tags'),
    'email':                trait_ds.get('submitter_email'),
    'institution':          trait_ds.get('institution'),
    'source_lab':           trait_ds.get('source_lab'),
    'protocols':            trait_ds.get('protocols'),
    'publication':          trait_ds.get('publication')
  }
  form = TraitSubmissionForm(data=form_data)
  return render_template('data/submit-trait-form.html', **{
    # Page Info
    'title':                      'Edit Trait',
    'tool_alt_parent_breadcrumb': { "title": trait_ds['trait_name_display_1'], "url": url_for(f'data.{return_to}', trait_id=trait_ds['name']) },
    'new_submission':             False,

    # Data
    'form':             form,
    'phenotype_values': [ v.to_json() for v in get_phenotype_values_for_trait(id) ],
    'file':             {
                          'name':       trait_ds['filename'],
                          'created_on': datetime.strftime(trait_ds['created_on'], "%Y-%m-%d"),
                        },
    'trait_id':         id,
    'user_is_admin':    user_is_admin(),

    'return_to': return_to,
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
                              StrainValidator( 'strain', species=species, force_unique=True, force_unique_msgs={}, strain_issues=None ),
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
  

@data_bp.route('/trait/<string:id>/download-file')
@cache.memoize(60*60)
@jwt_required()
def download_trait_file(id):
  """ Download the trait file """
  user = get_current_user()
  trait_ds = TraitFile.get_ds(id)
  if user_is_trait_owner(trait_ds.serialize(), user) and not user_is_admin():
    return abort(401)
  
  file = download_blob_to_file(MODULE_DB_OPERATIONS_BUCKET_NAME, trait_ds.get_filepath()[1], destination=UPLOADS_DIR)
  mimetype = get_file_format('tsv')['mimetype']
  return send_file(file, mimetype=mimetype, as_attachment=True, attachment_filename=trait_ds['filename'].raw_string)


def parse_trait_file(file):
  """ Parse a trait file into a list of dictionaries """
  with open(file) as f:
    file_content = []
    for idx, row in enumerate( csv.reader(f, delimiter='\t') ):
      file_content.append({'col_1': row[0], 'col_2': row[1]})
    return file_content
