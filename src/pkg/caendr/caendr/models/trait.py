import pandas as pd
from typing import Optional

from caendr.services.logger import logger

from caendr.models.datastore import TraitFile
from caendr.models.error     import NotFoundError
from caendr.models.error     import PublishStatusError
from caendr.models.status    import PublishStatus
from caendr.models.sql       import PhenotypeMetadata, PhenotypeDatabase
from caendr.utils.data       import dataframe_cols_to_dict

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

  def __init__(self, dataset = None, trait_name = None, trait_file_id = None, trait_file = None):
    self.name = trait_name

    # Trait file passed directly -- store it as-is
    if trait_file:
      self.file = trait_file

    # Trait file id -- retrieve from datastore
    elif trait_file_id:
      self.file = TraitFile.get_ds(trait_file_id, silent=False)

    # Special case: Zhang bulk file -- retrieve to single bulk file entry
    # TODO: We might be able to generalize this if we enforce that every dataset has to either
    #       have a single bulk file (and nothing else), or some number of non-bulk files (and no bulk files).
    #       We could then query by dataset and check the output to determine what TraitFile to use.
    elif dataset == 'zhang':
      self.file = TraitFile.query_ds_unique('dataset', dataset, required=True)

    # Dataset -- query by name and dataset
    elif dataset:
      self.file = TraitFile.query_ds(filters=[('trait_name_caendr', '=', trait_name), ('dataset', '=', dataset)])[0]

    # Fallback -- Query by trait name
    elif trait_name:
      self.file = TraitFile.query_ds_unique('trait_name_caendr', trait_name, required=True)

    # If none of the above were provided, there's not enough info to uniquely specify the trait
    else:
      raise ValueError('Could not identify a unique trait from the given information')

    # Store the dataset value of the trait file
    if dataset and self.file['dataset'] and dataset != self.file['dataset']:
      raise ValueError('Mismatched dataset values')
    self.dataset = self.file['dataset']


  #
  # Constructors
  #

  @classmethod
  def from_id(cls, trait_id: str) -> 'Trait':
    '''
      Instantiate a `Trait` object from a unique trait ID.
      The given ID must exist in the PhenotypeMetadata SQL table, otherwise a `ValueError` will be raised.
    '''

    # Get the SQL row with the given trait ID
    sql_row = PhenotypeMetadata.query.get(trait_id)
    if sql_row is None:
      raise NotFoundError(PhenotypeMetadata, {'id': trait_id})

    # Construct a Trait object using the data in the SQL row
    return cls(
      trait_name = sql_row.trait_name_caendr,
      dataset    = sql_row.dataset,
    )

  @classmethod
  def from_dataset(cls, dataset: str, trait_name: Optional[str] = None) -> 'Trait':
    return cls( dataset = dataset, trait_name = trait_name )

  @classmethod
  def from_datastore(cls, trait_file: TraitFile, trait_name: Optional[str] = None) -> 'Trait':
    if trait_file['is_bulk_file'] and trait_name is None:
      raise ValueError()
    return cls(
      dataset    = trait_file['dataset'],
      trait_name = trait_name if trait_name else trait_file['trait_name_caendr'],
      trait_file = trait_file,
    )

  @classmethod
  def from_sql(cls, sql_row: PhenotypeMetadata) -> 'Trait':
    return cls(
      dataset    = sql_row.dataset,
      trait_name = sql_row.trait_name_caendr,
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
      PhenotypeDatabase.query.filter( PhenotypeDatabase.trait_name == self.name ).statement, con=db.engine
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
  # Computing Display Name
  #

  @property
  def display_name(self):
    '''
      Compute the display name for this trait.
    '''

    # For bulk files, store the single trait name, otherwise convert the display_name fields to a list
    return (self.name,) if self.file['is_bulk_file'] else self.file.display_name


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
