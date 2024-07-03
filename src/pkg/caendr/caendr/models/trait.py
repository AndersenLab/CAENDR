import pandas as pd
from typing import Optional

from caendr.services.logger import logger

from caendr.models.datastore import TraitFile
from caendr.models.error     import NotFoundError
from caendr.models.error     import PublishStatusError
from caendr.models.status    import PublishStatus
from caendr.models.sql       import PhenotypeMetadata, PhenotypeDatabase
from caendr.models.error     import NotFoundError
from caendr.utils.data       import dataframe_cols_to_dict
from caendr.api.phenotype    import get_trait

from caendr.services.cloud.postgresql import db



class Trait():
  '''
    Utility class for converting between different representations of the same trait:
      - Dataset + unique name
      - Datastore unique ID
      - SQL metadata row / value query

    Tracks a trait file, and if it's a bulk file, a unique trait name within that file.

    TODO: Ideally an intermediary like this wouldn't be necessary. Can we simplify trait representation?
  '''


  #
  # Initialization
  #

  def __init__(self, trait_id: str, trait_file: Optional[TraitFile] = None, trait_row: Optional[PhenotypeMetadata] = None):

    # Look up the trait row, or use the one that's provided
    if trait_row:
      self.sql_row = trait_row
    else:
      self.sql_row = PhenotypeMetadata.query.get( trait_id )
      if self.sql_row is None:
        raise NotFoundError(PhenotypeMetadata, {'id': trait_id})

    # Look up the trait file, or use the one that's provided
    if trait_file:
      self.file = trait_file
    else:
      if self.sql_row.is_bulk_file:
        self.file = TraitFile.get_ds(self.sql_row.id.rsplit('_', 1)[0], silent=False)
      else:
        self.file = TraitFile.get_ds(trait_id, silent=False)


  #
  # Constructors
  #

  @classmethod
  def from_id(cls, trait_id: str) -> 'Trait':
    '''
      Instantiate a `Trait` object from a unique trait ID.
      The given ID must exist in the PhenotypeMetadata SQL table, otherwise a `ValueError` will be raised.
    '''

    return cls(trait_id)

  @classmethod
  def from_datastore(cls, trait_file: TraitFile, trait_name: Optional[str] = None) -> 'Trait':

    # Make sure a specific trait is selected if using a bulk file
    if trait_file['is_bulk_file'] and trait_name is None:
      raise ValueError('The given trait file is a bulk file, so a specific trait name must be provided')

    # Special parsing to get the SQL row for a bulk file
    if trait_file['is_bulk_file']:
      sql_row = PhenotypeMetadata.query.filter( PhenotypeMetadata.id.startswith(trait_file.name), PhenotypeMetadata.trait_name_caendr == trait_name ).one()
    else:
      sql_row = None

    # Pass ID along with both computed data sources
    return cls(
      trait_id   = trait_file.name,
      trait_file = trait_file,
      trait_row  = sql_row,
    )

  @classmethod
  def from_sql(cls, sql_row: PhenotypeMetadata) -> 'Trait':

    # Initialize from the SQL row ID value
    return cls(
      trait_id  = sql_row.id,
      trait_row = sql_row,
    )


  #
  # Querying
  #

  def query_values_dataframe(self):
    '''
      Query the measurements of this trait as a Pandas dataframe.
      Resulting dataframe will have the columns `strain_name` and `trait_value`.
    '''
    return pd.read_sql_query(
      PhenotypeDatabase.query.filter( PhenotypeDatabase.metadata_id == self.trait_id ).statement, con=db.engine
    )

  def query_values_dict(self):
    '''
      Query the measurements of this trait as a Python dict, mapping strain name to measured trait value.
    '''
    return self.dataframe_to_dict( self.query_values_dataframe() )

  @classmethod
  def dataframe_to_dict(cls, df):
    '''
      Convert a Trait dataframe (as produced by `Trait.query_values_dataframe`) to a Python dict,
      mapping strain name to measured trait val.
    '''
    return dataframe_cols_to_dict(df, 'strain_name', 'trait_value', drop_na=True)


  #
  # Properties
  #

  @property
  def trait_id(self):
    return self.sql_row.id

  @property
  def name(self):
    return self.sql_row.trait_name_caendr

  @property
  def dataset(self):
    return self.sql_row.dataset

  @property
  def display_name(self):
    '''
      Compute the display name for this trait.
    '''

    # For bulk files, store the single trait name, otherwise convert the display_name fields to a list
    return (self.sql_row.trait_name_caendr,) if self.file['is_bulk_file'] else self.file.display_name


  #
  # Updating Status
  #

  def __change_publish_status(self, to_state: PublishStatus):
    '''
      Change the publish status of this trait in both the Datastore and the SQL table.
      Validates that the new state is a valid transition from the current one.
    '''

    # Validate state transition
    # This handles argument type-checking
    if not PublishStatus.is_valid_transition(self.file['publish_status'], to_state):
      raise PublishStatusError(self.file['publish_status'], to_state)

    # Try changing the status on the TraitFile object
    try:
      self.file.change_publish_state(to_state)
      self.file.save()

    # Intercept errors to log, then continue propagating
    # If changing the file fails, we don't want to touch the SQL table
    except Exception as ex:
      logger.error(f'Failed to update PublishStatus of trait {self.name}: {ex}')
      raise

    # Try changing the status in the SQL table
    try:
      PhenotypeMetadata.query.get(self.file.name).set_status(to_state)

    # If the datastore entity was updated but the SQL table wasn't, log a critical error
    # and continue propagating the error
    except Exception as ex:
      logger.critical(
        f'Failed to update SQL table {PhenotypeMetadata.__tablename__} entry {self.name}'
        f'to match new PublishStatus of corresponding {TraitFile.kind} entity.'
        f'The datastore and the SQL table may now be out-of-sync.'
      )
      raise


  def submit(self):
    '''
      Submit this trait for review.
    '''
    return self.__change_publish_status(PublishStatus.SUBMITTED)


  def accept(self):
    '''
      Accept this trait into the public database.
    '''
    return self.__change_publish_status(PublishStatus.ACCEPTED)


  def reject(self):
    '''
      Reject this trait from entering the public database.
    '''
    return self.__change_publish_status(PublishStatus.UPLOADED)


  def retract(self):
    '''
      Retract this trait in the public database.
    '''
    return self.__change_publish_status(PublishStatus.RETRACTED)
