from functools import wraps
from typing    import Type

from flask import abort, redirect, request, url_for, flash

from base.utils.tools           import lookup_report

from caendr.models.datastore    import DatasetRelease, Species
from caendr.models.error        import NotFoundError, ReportLookupError, EmptyReportDataError, EmptyReportResultsError
from caendr.models.job_pipeline import JobPipeline
from caendr.services.logger     import logger



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
