import bleach
import os
from typing import Optional, Union, Iterable

from sqlalchemy import or_, func

from caendr.models.datastore import Species, User
from caendr.models.sql import PhenotypeMetadata
from caendr.services.cloud.postgresql import rollback_on_error



def query_phenotype_metadata(
    include_values = False,
    is_bulk_file: Optional[bool]                = None,
    dataset:      Optional[str]                 = None,
    species:      Optional[Union[Species, str]] = None,
    user:         Optional[Union[User, str]]    = None,
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
    query = filter_trait_query_by_species(query, species)
    query = filter_trait_query_by_user(query, user)

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



#
# Query Filters
#
# Conditionally add common filter types to a query object
#


def filter_trait_query(
    query,
    search_val: Optional[str]                 = None,
    tags:       Optional[Iterable[str]]       = None,
    species:    Optional[Union[Species, str]] = None,
    user:       Optional[Union[User, str]]    = None,
  ):
  '''
    Combined filtering function.
  '''
  query = filter_trait_query_by_text(query, search_val)
  query = filter_trait_query_by_tags(query, tags)
  query = filter_trait_query_by_species(query, species)
  query = filter_trait_query_by_user(query, user)
  return query


def filter_trait_query_by_text(query, search_val: Optional[str]):
  '''
    Filter by a text search value on the text fields.
    Generic "search" functionality.
  '''
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


def filter_trait_query_by_tags(query, tags: Optional[Iterable[str]]):
  '''
    Filter by trait tags.
  '''
  if tags and len(tags):
    query = query.filter(or_(
      PhenotypeMetadata.tags.ilike(f"%{bleach.clean(tag)}%") for tag in tags
    ))
  return query


def filter_trait_query_by_user(query, user: Optional[Union[User, str]]):
  '''
    Filter by submitting user.

    If username is invalid, passes error raised by `User` class.
  '''
  if user:

    # Cast string value to User object using unique datastore ID
    if isinstance(user, str):
      user = User.get_ds(user)

    # Validate user type
    if not isinstance(user, User):
      raise ValueError(f'Expected user, got {user}')

    # Filter by the username
    query = query.filter_by(submitted_by=user.full_name)

  return query


def filter_trait_query_by_species(query, species: Optional[Union[Species, str]]):
  '''
    Filter by species.

    If species is invalid, passes error raised by `Species` class.
  '''
  if species is not None:

    # Cast string value to Species object
    if isinstance(species, str):
      species = Species.from_name(species)

    # Validate species type
    if not isinstance(species, Species):
      raise ValueError(f'Expected species identifier, got {species}')

    # Filter by the species name
    query = query.filter_by(species_name=species.name)

  # Return the (possibly filtered) query
  return query
