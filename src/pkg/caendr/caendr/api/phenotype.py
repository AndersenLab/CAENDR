import bleach
import os

from sqlalchemy import or_, func

from caendr.models.datastore import Species
from caendr.models.error import BadRequestError
from caendr.models.sql import PhenotypeMetadata
from caendr.services.cloud.postgresql import rollback_on_error


def query_phenotype_metadata(is_bulk_file=False, include_values=False, species: str = None):
    """
      Returns the list of traits with the corresponding metadata.

      Args:
      - is_bulk_file:     by default returns data for non-bulk files
                          if 'is_bulk_file' set to True returns traits metadata for Zhang Expression file
      - phenotype_values: if True, include phenotype values for each trait
      - species:          filters by species
    """
    query = PhenotypeMetadata.query

    # Get traits for bulk file
    if is_bulk_file:
      query = query.filter_by(is_bulk_file=True)
    else:
      # Get traits for non-bulk files
      query = query.filter_by(is_bulk_file=False)

    # Query by species
    if species is not None:
      if species in Species.all().keys():
        query = query.filter_by(species=species)
      else:
        raise BadRequestError(f'Unrecognized species ID "{species}".')
    
    # Include phenotype values for traits
    if include_values:
       query = query.join(PhenotypeMetadata.phenotype_values)

    return query


def get_all_traits_metadata():
    """
      Returns metadata for all traits
    """
    return PhenotypeMetadata.query.all()


def get_trait(trait_name):
   return PhenotypeMetadata.query.get(trait_name)


def filter_trait_query_by_text(query, search_val):
  print(search_val)
  if search_val and len(search_val):
    query = query.filter(
      or_(
        PhenotypeMetadata.trait_name_caendr.ilike(f"%{search_val}%"),
        PhenotypeMetadata.trait_name_user.ilike(f"%{search_val}%"),
        PhenotypeMetadata.description_short.ilike(f"%{search_val}%"),
        PhenotypeMetadata.description_long.ilike(f"%{search_val}%"),
        PhenotypeMetadata.source_lab.ilike(f"%{search_val}%"),
        PhenotypeMetadata.institution.ilike(f"%{search_val}%"),
        PhenotypeMetadata.submitted_by.ilike(f"%{search_val}%"),
      )
    )
  return query


def filter_trait_query_by_tags(query, tags):
  if len(tags):
    query = query.filter(or_(
      PhenotypeMetadata.tags.ilike(f"%{bleach.clean(tag)}%") for tag in tags
    ))
  return query
