import bleach
from functools import wraps

from flask import request, Blueprint, abort
from caendr.services.logger import logger
from extensions import cache

from caendr.api.phenotype import query_phenotype_metadata, get_trait, filter_trait_query
from caendr.services.cloud.postgresql import rollback_on_error_handler

from caendr.models.datastore import TraitFile, Species
from caendr.models.error     import NotFoundError
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
  if _type: v = _type(v)

  return v


def query_traits_error_handler(f):
  '''
    Wrapper for trait query endpoints.
    If query raises an error, returns an empty response and a `500` error.
  '''
  @wraps(f)
  def inner(*args, **kwargs):
    try:
      return f(*args, **kwargs)
    except Exception as ex:
      logger.error(f'Failed to retrieve the list of traits: {ex}')
      return {}, 500
  return inner



#
# Query Endpoints
#


@api_trait_bp.route('/query', methods=['POST'])
@cache.memoize(60*60)
@query_traits_error_handler
@jsonify_request
def query():
  '''
    Query all trait files, optionally split into different lists based on species.
  '''

  # Get query filters (search parameters)
  selected_tags  = get_clean(request.json, 'selected_tags', [])
  search_val     = get_clean(request.json, 'search_val',    '').lower()
  filter_dataset = get_clean(request.json, 'dataset')

  # Get query pagination values
  page           = get_clean(request.json, 'page',         1, _type=int)
  current_page   = get_clean(request.json, 'current_page', 1, _type=int)
  per_page       = 10

  # Create the initial query
  query = query_phenotype_metadata(dataset=filter_dataset)

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
