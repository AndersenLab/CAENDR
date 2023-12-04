from flask import request, Blueprint, abort
from caendr.services.logger import logger
from extensions import cache

from caendr.models.datastore import TraitFile, Species
from caendr.models.error     import NotFoundError
from caendr.utils.json       import jsonify_request


api_trait_bp = Blueprint(
  'api_trait', __name__
)



def filter_trait_files(tf):
  return tf.is_public and not tf.is_bulk_file


@api_trait_bp.route('/all', methods=['GET'])
@cache.memoize(60*60)
@jsonify_request
def query_all():
  '''
    Query all trait files, optionally split into different lists based on species.
  '''

  # Optionally split into an object w species names for keys
  if request.args.get('split_by_species', False):
    return {
      species: [ tf.serialize() for tf in tf_list ]
        for species, tf_list in TraitFile.query_ds_split_species(filter=filter_trait_files).items()
    }

  # Otherwise, return all trait files in one list
  return [ tf.serialize() for tf in TraitFile.query_ds(ignore_errs=True) if filter_trait_files(tf) ]


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
