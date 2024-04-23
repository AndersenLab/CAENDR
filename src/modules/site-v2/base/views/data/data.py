import yaml
import bleach
import csv

from flask      import render_template, Blueprint, redirect, url_for, request, flash, jsonify, abort
from extensions import cache
from config     import config

from caendr.models.error           import EnvVarError, FileUploadError
from caendr.models.datastore       import TraitFile, Species
from caendr.models.status          import PublishStatus
from caendr.services.cloud.storage import get_blob, upload_blob_from_file_object, check_blob_exists
from caendr.services.logger        import logger
from caendr.services.validate      import validate_file, StrainValidator, NumberValidator
from caendr.utils.data             import unique_id
from base.utils.auth               import jwt_required, get_current_user
from caendr.utils.env              import get_env_var
from caendr.utils.local_files      import LocalUploadFile
from base.forms                    import TraitSubmissionForm
from constants                     import TOOL_INPUT_DATA_VALID_FILE_EXTENSIONS
from caendr.models.sql             import PhenotypeMetadata, PhenotypeDatabase





MODULE_DB_OPERATIONS_BUCKET_NAME = get_env_var('MODULE_DB_OPERATIONS_BUCKET_NAME')
MODULE_DB_OPERATIONS_TRAITFILE_PUBLIC_FILEPATH = get_env_var('MODULE_DB_OPERATIONS_TRAITFILE_PUBLIC_FILEPATH')

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
@data_bp.route('/submit-trait')
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
@data_bp.route('/submit-trait/new-submission', methods=['GET', 'POST'])
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
      try:
        # Create a new TraitFile object
        tf = TraitFile(unique_id())

        # Create a unique filename for file upload
        hashed_filename = f'{unique_id()}.tsv'

        tf.set_properties(**{
          # User submitted data
          'trait_name_user':      bleach.clean(form.trait_name_user.data),
          'trait_name_display_1': bleach.clean(form.trait_name_display_1.data),
          'trait_name_display_2': bleach.clean(form.trait_name_display_2.data),
          'trait_name_display_3': bleach.clean(form.trait_name_display_2.data),
          'filename':             bleach.clean(form.file.data.filename),
          'species':              bleach.clean(form.species.data),
          'description_short':    bleach.clean(form.description_short.data),
          'description_long':     bleach.clean(form.description_long.data),
          'units':                bleach.clean(form.units.data),
          'tags':                 [ bleach.clean(tag) for tag in form.tags.data ],
          'institution':          bleach.clean(form.institution.data),
          'source_lab':           bleach.clean(form.source_lab.data),
          'protocols':            bleach.clean(form.protocols.data),
          'publication':          bleach.clean(form.publication.data),
  
          # Internally used data
          'dataset':           'public',
          'publish_status':    PublishStatus.UPLOADED,
          'is_bulk_file':      False,
          'hashed_filename':   hashed_filename,
        })

        tf.set_user(user)

        # Save the TraitFile object to Datastore
        tf.save()

        # Seed to Phenotype Metadata SQL table
        new_trait = PhenotypeMetadata()
        new_trait.add_trait(tf)

      except Exception as ex:
        logger.error(f'Failed to create a trait file {form.trait_name_user.data}: {ex}')
        flash('Failed to submit a form. Please try again later.', 'danger')
        abort(500)
      
      # Save file to GCP bucket
      species_name = Species.get(form.species.data).name
      blob_name = f'{MODULE_DB_OPERATIONS_TRAITFILE_PUBLIC_FILEPATH}/{species_name}/{user.name}/{hashed_filename}'

      # Check if the file already exists
      if check_blob_exists(MODULE_DB_OPERATIONS_BUCKET_NAME, blob_name):
        flash('File already exists.', 'danger')
      else:
        upload_blob_from_file_object(MODULE_DB_OPERATIONS_BUCKET_NAME, form.file.data, blob_name)

      # Reset the file pointer
      form.file.data.seek(0)
        
      try:
        # Seed the file data to Phenotype Database SQL table
        with LocalUploadFile(form.file.data, valid_file_extensions=TOOL_INPUT_DATA_VALID_FILE_EXTENSIONS) as file:

          # Validate the file
          try:
            validate_file(file, [
                                  StrainValidator( 'strain', species=tf['species'], force_unique=True, force_unique_msgs={} ),
                                  NumberValidator( None, accept_float=True, accept_na=True ),
                                ])
          except Exception as ex:
            flash(f'Failed to validate the file: {ex.msg}', 'danger')
            return render_template('data/submit-trait-form.html', **{
              # Page Info
              'title': 'Phenotype Database Trait Submission',
              'tool_alt_parent_breadcrumb': {"title": "Submit Trait", "url": url_for('data.submit_trait_start')},

              # Data
              'form': form,
            })
          
          # Parse the trait file
          trait_data_list = []
          with open(file) as f:
            for idx, row in enumerate( csv.reader(f, delimiter='\t') ):
              if idx == 0:
                continue
              else:
                trait_data = {
                  'trait_name':  tf['trait_name_user'],
                  'strain_name': row[0],
                  'trait_value': row[1],
                  'metadata_id': tf.name
                }
                trait_data_list.append(trait_data)

        trait_data = PhenotypeDatabase()
        trait_data.add_trait_data(trait_data_list)

      except FileUploadError as ex:
        logger.error(f'Failed to upload a file {form.file.data.filename}: {ex}')
        flash('Failed to submit a form. Please try again later.', 'danger')
        abort(500)
      
      flash('Trait submitted successfully.', 'success')

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
@data_bp.route('/submit-trait/parse-file', methods=['POST'])
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
