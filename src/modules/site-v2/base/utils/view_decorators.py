import bleach
from functools import wraps
from typing    import Type

from flask     import abort, redirect, request, url_for, flash, jsonify
from flask_wtf import FlaskForm

from base.utils.auth            import user_is_admin
from base.utils.tools           import lookup_report, get_upload_err_msg
from constants                  import TOOL_INPUT_DATA_VALID_FILE_EXTENSIONS

from caendr.models.datastore    import DatasetRelease, Species
from caendr.models.error        import NotFoundError, ReportLookupError, EmptyReportDataError, EmptyReportResultsError, FileUploadError
from caendr.models.job_pipeline import JobPipeline
from caendr.services.logger     import logger
from caendr.utils.local_files   import LocalUploadFile



def parse_species(f):
  '''
    Parse `species_name` string argument from the URL into a `Species` object.

    Aborts with `404` if species name was not valid.
  '''

  @wraps(f)
  def decorator(*args, species_name, **kwargs):

    # Parse the species & release from the URL
    try:
      species = Species.from_name(species_name, from_url=True)

    # The `from_name` method always raises a NotFoundError if the name is not valid
    except NotFoundError:
      return abort(404)

    # If species name provided with underscore instead of dash, redirect to dashed version of URL
    if species.get_slug() != species_name:
      return redirect( url_for(request.endpoint, *args, species_name=species.get_slug(), **kwargs) )

    # Pass the objects to the function
    return f(*args, species=species, **kwargs)

  return decorator



def parse_species_and_release(f):
  '''
    Parse `species_name` and `release_version` string arguments from the URL
    into a `Species` object and `DatasetRelease` object, respectively.

    If `release_version` is omitted, defaults to latest release for the given species.

    Aborts with `404` if either was not valid.
  '''

  @wraps(f)
  def decorator(*args, species_name, release_version=None, **kwargs):

    # Parse the species & release from the URL
    try:
      species = Species.from_name(species_name, from_url=True)
      release = DatasetRelease.from_name(release_version, species_name=species.name)

    # The `from_name` method always raises a NotFoundError if the name is not valid
    except NotFoundError:
      return abort(404)
    
    # If species name provided with underscore instead of dash, redirect to dashed version of URL
    if species.get_slug() != species_name:
      return redirect( url_for(request.endpoint, *args, species_name=species.get_slug(), release_version=release_version, **kwargs) )

    # Pass the objects to the function
    return f(*args, species=species, release=release, **kwargs)

  return decorator



def parse_job_id(pipeline_class: Type[JobPipeline], fetch=True, check_data_exists=True):
  '''
    Parse `report_id` string argument from the URL into a `JobPipeline` subclass object,
    and pre-fetches the data and results if desired.

    Aborts with `404` if report ID was invalid, or optionally if no input data could be fetched.

    Arguments:
      - `pipeline_class`: The `JobPipeline` subclass to use to lookup the report.
      - `fetch`: If `True`, pre-fetch the input `data` and output `result`, and pass them to the wrapped function as keyword arguments.
      - `check_data_exists`: If `True`, abort with `404` if the fetched input data is `None`.
  '''

  def wrapper(f):

    @wraps(f)
    def decorator(*args, report_id, **kwargs):

      # Fetch requested phenotype report
      # Ensures the report exists and the current user has permission to view it
      try:
        job = lookup_report(pipeline_class.get_kind(), report_id)

      # If the report lookup request is invalid, show an error message
      except ReportLookupError as ex:
        flash(ex.msg, 'danger')
        abort(ex.code)

      # Optionally bail out here -- don't bother fetching data/results
      if not fetch:
        return f(*args, job=job, **kwargs)

      # Try getting & parsing the report data file and results
      # If result is None, job hasn't finished computing yet
      try:
        data, result = job.fetch()

      # Error reading one of the report files
      except (EmptyReportDataError, EmptyReportResultsError) as ex:
        logger.error(f'Error fetching {pipeline_class.get_kind()} report {ex.id}: {ex.description}')
        return abort(404, description = ex.description)

      # General error
      except Exception as ex:
        logger.error(f'Error fetching {pipeline_class.get_kind()} report {id}: {ex}')
        return abort(400, description = 'Something went wrong')

      # Check that data file exists, if desired
      if check_data_exists and data is None:
        logger.error(f'Error fetching {pipeline_class.get_kind()} report {id}: Input data file does not exist')
        return abort(404)

      # Pass the objects to the function
      return f(*args, job=job, data=data, result=result, **kwargs)

    return decorator
  return wrapper



def validate_form(form_class: Type[FlaskForm], from_json: bool = False, err_msg: str = None, flash_err_msg: bool = True):
  '''
    Parse the request form into the given form type, validate the fields, and inject the data as a dict.

    Aborts with `400` if form validation fails.

    TODO: What happens with non-None `form_class` and `from_json = True`? Can FlaskForm initialize that way?

    Passes the following args to the wrapped function:
      - `form_data`: A dict of cleaned / validated fields from the form.
      - `no_cache`: Whether the user wants to skip caching the form results. Can only be set if user is admin.

    Arguments:
      - `form_class`: The `FlaskForm` subclass to use for parsing/validation. If `None`, cleans the individual fields but performs no form validation.
      - `from_json`: If `True`, use the request `.get_json()` as the fields instead.
      - `err_msg`: An error message to add to the response if validation fails.
      - `flash_err_msg`: If `True`, flashes the `err_msg` in addition to returning it.
  '''

  def wrapper(f):

    def _clean_field(value):
      ''' Helper function: apply bleach.clean to value, if applicable '''
      try:
        return bleach.clean(value)
      except TypeError:
        return value

    @wraps(f)
    def decorator(*args, **kwargs):

      # If user is admin, allow them to bypass cache with URL variable
      no_cache = bool(user_is_admin() and request.args.get("nocache", False))

      # Pull the raw data from either the form or the JSON body
      raw_data = request.get_json() if from_json else request.form

      # If no form class provided
      if form_class is None:
        return f(*args, form_data={ k: _clean_field(v) for k, v in raw_data.items() }, no_cache=no_cache, **kwargs)

      # Construct the Flask form object
      form = form_class(request.form)

      # Validate form fields
      if not form.validate_on_submit():
        if err_msg and flash_err_msg:
          flash(err_msg, 'danger')
        return jsonify({ 'message': err_msg, 'errors': form.errors }), 400

      # Read & clean fields from form, excluding CSRF token & file upload(s)
      form_data = {
        field.name: _clean_field(field.data) for field in form if field.name in request.form and field.id != 'csrf_token'
      }

      # If no file(s) uploaded, evaluate here
      if not len(request.files):
        return f(*args, form_data=form_data, no_cache=no_cache, **kwargs)

      # Upload input file to server temporarily and add to the list of form fields
      # TODO: This hardcodes the field name 'file' for a *single* file upload -- generalize whatever file field(s) are present
      try:
        with LocalUploadFile(request.files['file'], valid_file_extensions=TOOL_INPUT_DATA_VALID_FILE_EXTENSIONS) as local_file:

          # Pass the objects to the function
          return f(*args, form_data={**form_data, 'file': local_file}, no_cache=no_cache, **kwargs)

      # If the file upload failed, display an error message
      except FileUploadError as ex:
        message = get_upload_err_msg(ex.code)
        flash(message, 'danger')
        return jsonify({ 'message': message }), ex.code

    return decorator
  return wrapper
