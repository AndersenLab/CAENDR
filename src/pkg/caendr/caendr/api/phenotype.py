import bleach
import os
from typing import Optional, Union, Iterable

from sqlalchemy import or_, func

from caendr.models.datastore import Species, User
from caendr.models.sql import PhenotypeMetadata
from caendr.services.cloud.postgresql import rollback_on_error



def query_phenotype_metadata(
    include_values:  bool = False,
    include_private: bool = False,
    is_bulk_file: Optional[bool]                = None,
    dataset:      Optional[str]                 = None,
    species:      Optional[Union[Species, str]] = None,
    user:         Optional[Union[User, str]]    = None,
):
    """
      Create a trait metadata SQL query, with some optional initial filters.
      Returns a query object that can be further refined.

      Args:
        - `include_values`:  If `True`, includes the phenotype value measurements for each trait.
        - `include_private`: If `True`, includes private (unpublished) traits in the query.
        - `is_bulk_file`:    Optionally filter by whether the traits belong to a bulk dataset.
                             If `None`, does not filter by this parameter.
        - `dataset`:         Optionally filters by dataset.
        - `species`:         Optionally filters by species.
        - `user`:            Optionally filters by submitting user.
    """

    # Create the initial query
    query = PhenotypeMetadata.query

    # TODO: Filter by public (published) / private (unpublished)
    if not include_private:
      pass

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

    # Order alphabetically by trait names
    query = order_trait_query_by_name(query)

    return query


def get_all_traits_metadata():
  """
    Returns metadata for all traits
  """
  return PhenotypeMetadata.query.all()


def get_trait(trait_id):
  return PhenotypeMetadata.query.get(trait_id)


def order_trait_query_by_name(query):
  '''
    Sort a Phenotype Database trait query alphabetically by the display name(s).
  '''
  return query.order_by(

    # Order by display names, in order
    PhenotypeMetadata.trait_name_display_1.asc(),
    PhenotypeMetadata.trait_name_display_2.asc(),
    PhenotypeMetadata.trait_name_display_3.asc(),

    # Fallback to internal CaeNDR trait name
    PhenotypeMetadata.trait_name_caendr.asc(),
  )



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



#
# Trait Categories
#


@rollback_on_error
def get_trait_categories(query = None):
  '''
    Get the list of trait categories.

    If a query is provided, only returns categories represented in that query.
    Otherwise, creates a new query.

    TODO: Currently, uses PhenotypeMetadata table queries to get the full list
          of categories, as strings. In the future we may want to explicitly
          store this list somewhere and attach metadata.
  '''
  # If no query given, default to full-database search
  # TODO: We can speed this up a lot by excluding Zhang traits... what is the most data-agnostic way to do that?
  if query is None:
    query = query_phenotype_metadata()

  # Parse the list of tags from each row
  # `filter` with None removes all non-truthy values, i.e. empty tag sets
  tags = filter(None, ( tr.get_tags() for tr in query ))

  # Flatten the list of lists into a set, and sort the result
  tags_list = { tg for tr_tag in tags for tg in tr_tag }
  return sorted(tags_list)
