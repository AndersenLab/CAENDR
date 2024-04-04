import bleach
import os
from typing import Optional, Union

from sqlalchemy import or_, func

from caendr.models.datastore import Species
from caendr.models.sql import PhenotypeMetadata
from caendr.services.cloud.postgresql import rollback_on_error


def query_phenotype_metadata(
    include_values = False,
    is_bulk_file: Optional[bool]                = None,
    species:      Optional[Union[Species, str]] = None,
    dataset:      Optional[str]                 = None,
):
    """
      Returns the list of traits with the corresponding metadata.

      Args:
      - is_bulk_file:     by default returns data for non-bulk files
                          if 'is_bulk_file' set to True returns traits metadata for Zhang Expression file
      - phenotype_values: if True, include phenotype values for each trait
      - species:          filters by species
    """

    # Create the initial query
    query = PhenotypeMetadata.query

    # Optionally query by bulk file
    if is_bulk_file is not None:
      query = query.filter_by(is_bulk_file=bool(is_bulk_file))

    # Optionally query by dataset
    if dataset is not None:
      query = query.filter_by(dataset=dataset)

    # Optionally query by species
    # None values handled in function
    filter_trait_query_by_species(query, species)
    
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


def filter_trait_query_by_species(query, species: Optional[Union[Species, str]]):
  '''
    Filter by species.

    If species is invalid, passes error raised by `Species` class.
  '''
  if species is not None:

    # Cast string values to Species object
    if isinstance(species, str):
      species = Species.from_name(species)

    # Validate species type
    if not isinstance(species, Species):
      raise ValueError(f'Expected species identifier, got {species}')

    # Filter by the species name
    query = query.filter_by(species_name=species.name)

  # Return the (possibly filtered) query
  return query
