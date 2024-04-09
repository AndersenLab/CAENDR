import bleach
from functools import wraps
import json

from flask import request, Blueprint, abort, jsonify
from caendr.services.logger import logger
from extensions import cache, compress

from caendr.api.phenotype import query_phenotype_metadata, get_trait, filter_trait_query
from caendr.services.cloud.postgresql import rollback_on_error_handler

from caendr.models.datastore import Entity, TraitFile, Species, User
from caendr.models.error     import NotFoundError
from caendr.models.sql       import PhenotypeMetadata
from caendr.utils.json       import jsonify_request


api_trait_bp = Blueprint(
  'api_trait', __name__
)



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



#
# Query Endpoints: List Traits
#


@api_trait_bp.route('/list/sql', methods=['POST'])
@cache.memoize(60*60)
@query_traits_error_handler('Failed to retrieve the list of traits')
@jsonify_request
def query_list_sql():
  '''
    Query the trait database, and return results with SQL-style pagination.
  '''

  # Get query filters (search parameters)
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
  query = query_phenotype_metadata(dataset=filter_dataset, species=filter_species, user=filter_user)

  # Filter by search values, if provided
  query = filter_trait_query(query, search_val=search_val, tags=selected_tags)

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



@api_trait_bp.route('/list/datatable', methods=['GET'])
@cache.memoize(60*60)
@query_traits_error_handler('Failed to retrieve the list of traits')
@jsonify_request
def query_list_datatable():
  '''
    Query the trait database, and return results with DataTable-style pagination.
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
  query = query_phenotype_metadata(dataset=filter_dataset, species=filter_species, user=filter_user)
  total_records = query.count()

  # Filter by search values, if provided
  query = filter_trait_query(query, search_val=search_value, tags=selected_tags)

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
  trait_name = get_clean(request.json, 'trait_name')
  if not trait_name:
    abort(400, description='No trait name provided.')

  # Try getting the trait from the database
  trait = get_trait(trait_name)
  if trait is None:
    abort(404, description=f'Invalid trait name {trait_name}')

  # Return the full trait metadata
  return trait.to_json_with_values()
