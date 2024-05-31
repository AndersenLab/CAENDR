import bleach
from enum import Enum
from functools import wraps
import json

from flask import request, Blueprint, abort, jsonify
from caendr.services.logger import logger
from extensions import cache, compress

from base.utils.auth import jwt_required, get_current_user, user_is_admin, admin_required
from base.utils.view_decorators import parse_trait

from caendr.api.phenotype import query_phenotype_metadata, get_trait, filter_trait_query, get_trait_categories
from caendr.services.cloud.postgresql import rollback_on_error_handler

from caendr.models.datastore import Entity, TraitFile, Species, User
from caendr.models.error     import NotFoundError, PublishStatusError
from caendr.models.status    import PublishStatus
from caendr.models.trait     import Trait
from caendr.models.sql       import PhenotypeMetadata
from caendr.utils.json       import jsonify_request
from base.utils.auth         import jwt_required


api_trait_bp = Blueprint(
  'api_trait', __name__
)



#
# Helper Classes
#


class EndpointType(Enum):
  '''
    Enum class for trait API endpoint types.
    Requires endpoints to have the format "{ prefix }_{ value }", where `value` is one of the enum values.
  '''

  PUBLIC  = 'public'
  PRIVATE = 'private'
  QUEUE   = 'queue'
  ALL     = 'all'

  @classmethod
  def full(cls, endpoint_prefix, endpoint_type):
    return f'{ api_trait_bp.name }.{ endpoint_prefix }_{ endpoint_type.value }'

  @classmethod
  def matches(cls, endpoint: str, endpoint_type):
    return endpoint.endswith(endpoint_type.value)

  @classmethod
  def matches_any(cls, endpoint, endpoint_type_set):
    return any( cls.matches(endpoint, endpoint_type) for endpoint_type in endpoint_type_set )



#
# Helper Functions
#


def filter_trait_files(tf):
  return tf.is_public and not tf.is_bulk_file


def get_clean(source, key, value=None, _type=None):
  v = source.get(key, value)

  # Clean value
  if   isinstance(v, str):   v = bleach.clean(v)
  elif isinstance(v, list):  v = [ bleach.clean(x) for x in v ]

  # Optional typecasting
  if _type and v is not None:
    if issubclass(_type, Entity):
      v_entity = _type.get_ds(v)
      if v_entity is None:
        raise NotFoundError(_type, {'name': v})
      v = v_entity
    else:
      v = _type(v)

  return v


def query_traits_error_handler(err_msg):
  '''
    Wrapper for trait query endpoints.

    If the wrapped function aborts with an error code, that code will be used
    by the response. Otherwise, based on the error type, either a `404` or a
    `500` will be returned.
  '''

  def decorator(f):
    @wraps(f)
    def inner(*args, **kwargs):
      try:
        return f(*args, **kwargs)

      # Error handling
      except Exception as ex:

        # Choose error code based on error type
        if hasattr(ex, 'code'):
          err_code = ex.code
        elif isinstance(ex, NotFoundError):
          err_code = 404
        else:
          err_code = 500

        # Log the full error, and return the response with an abridged message
        logger.error(f'{err_msg}: {ex}')
        return {'message': f'{err_msg}'}, err_code

    return inner
  return decorator


def validate_user():
  '''
    Validate that the requesting user can access the current endpoint.
    Requires endpoint to be formatted according to `EndpointType` Enum.
  '''

  # On the "public" endpoint, no user validation required
  if EndpointType.matches( request.endpoint, EndpointType.PUBLIC ):
    return True

  # On the "private" endpoint, user must be logged in
  elif EndpointType.matches( request.endpoint, EndpointType.PRIVATE ):
    return get_current_user() is not None

  # On the "queue" endpoint, user must be an admin
  elif EndpointType.matches( request.endpoint, EndpointType.QUEUE ):
    return user_is_admin()

  # On the "all" endpoint, user must be an admin
  elif EndpointType.matches( request.endpoint, EndpointType.ALL ):
    return user_is_admin()

  # If some other endpoint is being requested here somehow, abort
  abort(404)


def validate_endpoint_type(endpoint_prefix):
  '''
    Validate that the user has permission to access this endpoint, based on the `EndpointType` schema.

    See `validate_user` for details.
  '''

  def decorator(f):
    @wraps(f)
    def inner(*args, **kwargs):

      # Validate that the current user has access to the specific endpoint they're requesting
      if not validate_user():
        abort(403)

      # On the "private" endpoint, only consider traits belonging to the current user
      if EndpointType.matches( request.endpoint, EndpointType.PRIVATE ):
        user_filter = get_current_user()
      else:
        user_filter = None

      # On the "public" endpoint, only consider public traits
      if EndpointType.matches( request.endpoint, EndpointType.PUBLIC ):
        status_filter = { PublishStatus.CANONICAL, PublishStatus.ACCEPTED }

      # On the "queue" endpoint, only consider traits that have been submitted but are not yet public
      elif EndpointType.matches( request.endpoint, EndpointType.QUEUE ):
        status_filter = { PublishStatus.SUBMITTED }

      # On all other endpoints, don't filter by status
      else:
        status_filter = None

      return f(*args, user_filter=user_filter, status_filter=status_filter, **kwargs)

    return inner
  return decorator



#
# Query Endpoints: List Traits
#


@api_trait_bp.route('/list/sql/public',  endpoint='query_list_sql_public',  methods=['POST'])
@api_trait_bp.route('/list/sql/private', endpoint='query_list_sql_private', methods=['POST'])
@api_trait_bp.route('/list/sql/queue',   endpoint='query_list_sql_queue',   methods=['POST'])
@api_trait_bp.route('/list/sql/all',     endpoint='query_list_sql_all',     methods=['POST'])
@cache.memoize(60*60)
@jwt_required(optional=True)
@validate_endpoint_type('query_list_sql')
@query_traits_error_handler('Failed to retrieve the list of traits')
@jsonify_request
def query_list_sql(user_filter=None, status_filter=None):
  '''
    Query the trait database using SQL-style pagination.

    Defines three separate endpoints:
      - `public`:  Queries traits that have been submitted to the public phenotype database.
      - `private`: Queries all traits that belong to the requesting user. Log-in required.
      - `all`:     Queries all traits that have been uploaded. Admin users only.

    Accepts the following URL variables to filter the request:
      - `dataset`: The phenotype dataset.
      - `species`: The species for the trait.
      - `user`:    The user that submitted the trait.

    Note that on the `private` endpoint, filtering the `user` parameter by anything other than
    the current user will return no results, since the two user filters are exclusive.
    This is still a syntactically valid request, but it is semantically invalid.
  '''

  # Get search parameters
  selected_tags  = get_clean(request.json, 'selected_tags', [])
  search_val     = get_clean(request.json, 'search_val',    '').lower()

  # Get other query filters
  try:
    filter_dataset = get_clean(request.args, 'dataset')
    filter_species = get_clean(request.args, 'species', _type=Species)
    filter_user    = get_clean(request.args, 'user',    _type=User)
  except NotFoundError as ex:
    abort(422, description=ex.description)

  # Get query pagination values
  page           = get_clean(request.json, 'page',         1, _type=int)
  current_page   = get_clean(request.json, 'current_page', 1, _type=int)
  per_page       = 10

  # Create the initial query
  # The filters here determine which traits are part of the "full" query,
  # based on the request endpoint
  query = query_phenotype_metadata(
    dataset=filter_dataset, user=user_filter, status=status_filter,
  )

  # Filter by search values, if provided
  query = filter_trait_query(
    query, search_val=search_val, tags=selected_tags, species=filter_species, user=filter_user,
  )

  # Paginate the query, rolling back on error
  with rollback_on_error_handler():
    pagination = query.paginate(page=page, per_page=per_page)

  # Format return data
  return {
    'data': [
      tr.to_json() for tr in pagination.items
    ],
    'pagination': {
      'has_next':     pagination.has_next,
      'has_prev':     pagination.has_prev,
      'prev_num':     pagination.prev_num,
      'next_num':     pagination.next_num,
      'total_pages':  pagination.pages,
      'current_page': current_page
    },
  }



@api_trait_bp.route('/list/datatable/public',  endpoint='query_list_datatable_public',  methods=['GET'])
@api_trait_bp.route('/list/datatable/private', endpoint='query_list_datatable_private', methods=['GET'])
@api_trait_bp.route('/list/datatable/queue',   endpoint='query_list_datatable_queue',   methods=['GET'])
@api_trait_bp.route('/list/datatable/all',     endpoint='query_list_datatable_all',     methods=['GET'])
@cache.memoize(60*60)
@jwt_required(optional=True)
@validate_endpoint_type('query_list_datatable')
@query_traits_error_handler('Failed to retrieve the list of traits')
@jsonify_request
def query_list_datatable(user_filter=None, status_filter=None):
  '''
    Query the trait database using DataTable-style pagination.

    Defines three separate endpoints:
      - `public`:  Queries traits that have been submitted to the public phenotype database.
      - `private`: Queries all traits that belong to the requesting user. Log-in required.
      - `all`:     Queries all traits that have been uploaded. Admin users only.

    Accepts the following URL variables to filter the request:
      - `dataset`: The phenotype dataset.
      - `species`: The species for the trait.
      - `user`:    The user that submitted the trait.

    Note that on the `private` endpoint, filtering the `user` parameter by anything other than
    the current user will return no results, since the two user filters are exclusive.
    This is still a syntactically valid request, but it is semantically invalid.
  '''

  # Load full search object from request
  search_raw = get_clean(request.args, 'search[value]', '')
  if search_raw:
    try:
      search_full = json.loads(search_raw)
    except:
      abort(422, description="Invalid search")

    # Treat non-dict values as search strings
    # Use the original raw string here so JSON casting doesn't change the value
    # (e.g. JSON "true" becoming Python "True")
    if not isinstance(search_full, dict):
      search_full = { 'search_val': search_raw }

  else:
    search_full = {}

  # Get search parameters from search object
  search_value  = get_clean(search_full, 'search_val', '').lower()
  selected_tags = get_clean(search_full, 'selected_tags', [])

  # Get other query filters
  try:
    filter_dataset = get_clean(request.args, 'dataset')
    filter_species = get_clean(request.args, 'species', _type=Species)
    filter_user    = get_clean(request.args, 'user',    _type=User)
  except NotFoundError as ex:
    abort(422, description=ex.description)

  # Get query pagination values
  draw   = get_clean(request.args, 'draw',   _type=int)
  start  = get_clean(request.args, 'start',  _type=int)
  length = get_clean(request.args, 'length', _type=int)

  # Create the initial query
  # The filters here determine which traits are part of the "full" query,
  # based on the request endpoint
  query = query_phenotype_metadata(
    dataset=filter_dataset, user=user_filter, status=status_filter,
  )

  # Count the full size of the query
  # Any rows filtered out before this line aren't available in this request at all,
  # and any rows filtered out after this line are considered filtered rows in the full request
  total_records = query.count()

  # Filter by search values, if provided
  query = filter_trait_query(
    query, search_val=search_value, tags=selected_tags, species=filter_species, user=filter_user,
  )

  # Query PhenotypeMetadata (include phenotype values for each trait)
  with rollback_on_error_handler():
    data = query.offset(start).limit(length).from_self().\
      join(PhenotypeMetadata.phenotype_values).all()

  # Count how many rows matched the filters
  filtered_records = query.count()

  # Format return data
  return {
    'data': [
      trait.to_json_with_values() for trait in data
    ],
    'draw':            draw,
    'recordsTotal':    total_records,
    'recordsFiltered': filtered_records,
  }



@api_trait_bp.route('/<species_name>', methods=['GET'])
@cache.memoize(60*60)
@jsonify_request
def query_species(species_name):
  '''
    Query all trait files for the given species.
  '''

  # Get the species from the URL
  try:
    species = Species.from_name(species_name, from_url=True)
  except NotFoundError:
    return abort(404)

  # Query, serialize, and return all trait files with the given species
  return [
    tf.serialize()
      for tf in TraitFile.query_ds(ignore_errs=True, filters=['species', '=', species.name])
      if filter_trait_files(tf)
  ]



#
# Query Endpoints: Single Trait
#


@api_trait_bp.route('/metadata', methods=['POST'])
@cache.memoize(60*60)
@compress.compressed()
@query_traits_error_handler('Failed to retrieve trait metadata')
@jsonify_request
def query_trait_metadata():
  """
    Get traits data for non-bulk files in JSON format (include phenotype values)
  """

  # Get the trait name from the request
  trait_id = get_clean(request.json, 'trait_id')
  if not trait_id:
    abort(400, description='No trait ID provided.')

  # Try getting the trait from the database
  trait = get_trait(trait_id)
  if trait is None:
    abort(404, description=f'Invalid trait ID {trait_id}')

  # Return the full trait metadata
  return trait.to_json_with_values()



#
# Query Endpoint: Trait Categories
#


@api_trait_bp.route('/categories', methods=['GET'])
@cache.memoize(60*60)
@compress.compressed()
@query_traits_error_handler('Failed to retrieve trait categories')
@jsonify_request
def query_trait_categories():
  """
    Get list of trait categories.
  """
  return get_trait_categories()



#
# Submission Queue ("Review") Endpoints
#


@api_trait_bp.route('/review/<string:trait_id>/submit', methods=['POST'])
@jwt_required()
@parse_trait(validate_owner=True, allow_admin=False)
@jsonify_request
def submit_trait(trait: Trait):
  '''
    Submit a trait file for admin review.
  '''

  # Try updating the trait status, aborting if the state transition is invalid
  try:
    trait.submit()
  except PublishStatusError as ex:
    logger.error(ex.description)
    abort(422, description=f'Cannot submit trait {trait.name}: current status is {ex.from_state}')

  # Return success
  return {}


@api_trait_bp.route('/review/<string:trait_id>/accept', methods=['POST'])
@admin_required()
@parse_trait()
@jsonify_request
def accept_trait(trait: Trait):
  '''
    Accept a new trait into the public database.
  '''

  # Try updating the trait status, aborting if the state transition is invalid
  try:
    trait.accept()
  except PublishStatusError as ex:
    logger.error(ex.description)
    abort(422, description=f'Cannot accept trait {trait.name}: current status is {ex.from_state}')

  # Return success
  return {}


@api_trait_bp.route('/review/<string:trait_id>/reject', methods=['POST'])
@admin_required()
@parse_trait()
@jsonify_request
def reject_trait(trait: Trait):
  '''
    Reject a trait file from entering the public database.
    The trait will be returned to the submitting user.
  '''

  # Try updating the trait status, aborting if the state transition is invalid
  try:
    trait.reject()
  except PublishStatusError as ex:
    logger.error(ex.description)
    abort(422, description=f'Cannot reject trait {trait.name}: current status is {ex.from_state}')

  # Return success
  return {}


@api_trait_bp.route('/review/<string:trait_id>/retract', methods=['POST'])
@admin_required()
@parse_trait()
@jsonify_request
def retract_trait(trait: Trait):
  '''
    Retract a published trait in the public database.

    The trait will not be removed or deleted; rather, it will be marked as retracted.
    This maintains consistency with any reports that depend on the trait.

    This is a rather extreme option, so it should only be used when absolutely necessary.
  '''

  # Try updating the trait status, aborting if the state transition is invalid
  try:
    trait.retract()
  except PublishStatusError as ex:
    logger.error(ex.description)
    abort(422, description=f'Cannot retract trait {trait.name}: current status is {ex.from_state}')

  # Return success
  return {}
