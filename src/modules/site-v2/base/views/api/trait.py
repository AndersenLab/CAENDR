from flask import request, Blueprint, abort
from caendr.services.logger import logger
from extensions import cache

from caendr.api.phenotype import query_phenotype_metadata, get_trait, filter_trait_query_by_text, filter_trait_query_by_tags
from caendr.services.cloud.postgresql import rollback_on_error_handler

from caendr.models.datastore import TraitFile, Species
from caendr.models.error     import NotFoundError
from caendr.utils.json       import jsonify_request


api_trait_bp = Blueprint(
  'api_trait', __name__
)



def filter_trait_files(tf):
  return tf.is_public and not tf.is_bulk_file


@api_trait_bp.route('/query', methods=['POST'])
@cache.memoize(60*60)
@jsonify_request
def query():
  '''
    Query all trait files, optionally split into different lists based on species.
  '''

  # Get query filters
  selected_tags  = request.json.get('selected_tags', [])
  search_val     = request.json.get('search_val',    '')
  filter_dataset = request.json.get('dataset',       None)

  # Get query pagination values
  page           = int(request.json.get('page', 1))
  current_page   = int(request.json.get('current_page', 1))
  per_page       = 10

  # Create the initial query
  query = query_phenotype_metadata(dataset=filter_dataset)

  # Filter by search values, if provided
  query = filter_trait_query_by_text(query, search_val)
  query = filter_trait_query_by_tags(query, selected_tags)

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
