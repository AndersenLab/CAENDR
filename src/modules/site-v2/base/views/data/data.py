import yaml

from flask      import render_template, Blueprint, redirect, url_for, request, flash
from extensions import cache
from config     import config

from caendr.models.error           import EnvVarError
from caendr.models.datastore       import TraitFile
from caendr.models.status          import PublishStatus
from caendr.services.cloud.storage import get_blob
from caendr.services.logger        import logger
from caendr.utils.data             import unique_id
from base.utils.auth               import jwt_required, get_current_user
from base.forms                    import TraitSubmissionForm




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
@data_bp.route('/submit-trait/start')
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
        tf.set_properties(**{
          # User submitted data
          'trait_name_user':   form.trait_name_user.data,
          'filename':          form.file.data.filename,
          'species':           form.species.data,
          'description_short': form.description_short.data,
          'description_long':  form.description_long.data,
          'units':             form.units.data,
          'tags':              form.tags.data,
          'username':          form.username.data,
          'institution':       form.institution.data,
          'source_lab':        form.source_lab.data,
          'protocols':         form.protocols.data,
          'publication':       form.publication.data,
  
          # Internally used data
          'dataset':        'public',
          'publish_status': PublishStatus.UPLOADED,
          'is_bulk_file':   False
        })
        tf.save()
        # TODO: save file to GCP
        # TODO: save the submission to My Trait Library
        return 'Form submitted successfully!'
      except Exception as ex:
        logger.error(f'Failed to create a trait file: {ex}')
        flash('Failed to submit a form. Please try again later.', 'error')
        return redirect(url_for('data.submit_trait_start'))

      
  return render_template('data/submit-trait-form.html', **{
    # Page Info
    'title': 'Submit Trait',
    'disable_parent_breadcrumb': True,

    # Data
    'form': form,

  })

