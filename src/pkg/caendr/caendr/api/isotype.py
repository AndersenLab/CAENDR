import os

from flask import request

from caendr.models.sql import Strain


photos_bucket = os.environ.get("MODULE_SITE_BUCKET_PHOTOS_NAME")
photos_path_prefix = os.environ.get("MODULE_IMG_THUMB_GEN_SOURCE_PATH")


def get_isotypes(known_origin=False, list_only=False, unique=False, species=None):
  """
    Returns a list of strains where isotype_ref_strain == True;
    Represents ONE strain per isotype. This is the reference strain.

    Args:
        known_origin: Returns only strains with a known origin
        list_only: Returns a list of isotypes (internal use)
        species: Optionally limit to one species. Default None.
  """
  # TODO: integrate these 2 legacy functions so the rest of the args are handled
  if unique:
    return get_distinct_isotypes()

  # Basic query for isotypes
  result = Strain.query.filter( Strain.isotype_ref_strain == True ).order_by( Strain.isotype )

  # Optionally limit to given species
  if species is not None:
    result = result.filter( Strain.species_name == species )

  # Optionally limit to strains where origin is known
  if known_origin or 'origin' in request.path:
    result = result.filter(Strain.latitude != None)

  result = result.all()
  if list_only:
    result = [x.isotype for x in result]
  return result


def get_distinct_isotypes():
  """
      Returns a list of unique values in the isotype column of the Strains table
  """
  result = Strain.query.with_entities(Strain.isotype).filter(Strain.isotype != None).distinct().all()
  result = [x.isotype for x in result]
  return result

