from enum import Enum


class DbOp(Enum):
  '''
    All possible database operation types.
  '''

  UPGRADE_DATABASE                            = 'UPGRADE_DATABASE'
  CREATE_DATABASE_MIGRATION                   = 'CREATE_DATABASE_MIGRATION'
  DROP_AND_POPULATE_STRAINS                   = 'DROP_AND_POPULATE_STRAINS'
  DROP_AND_POPULATE_WORMBASE_GENES            = 'DROP_AND_POPULATE_WORMBASE_GENES'
  DROP_AND_POPULATE_STRAIN_ANNOTATED_VARIANTS = 'DROP_AND_POPULATE_STRAIN_ANNOTATED_VARIANTS'
  DROP_AND_POPULATE_PHENOTYPE_DB              = 'DROP_AND_POPULATE_PHENOTYPE_DB'
  DROP_AND_POPULATE_PHENOTYPE_METADATA        = 'DROP_AND_POPULATE_PHENOTYPE_METADATA'
  DROP_AND_POPULATE_PHENOTYPES                = 'DROP_AND_POPULATE_PHENOTYPES'
  DROP_AND_POPULATE_ALL_TABLES                = 'DROP_AND_POPULATE_ALL_TABLES'
  POPULATE_PHENOTYPES_DATASTORE               = 'POPULATE_PHENOTYPES_DATASTORE'
  TEST_ECHO                                   = 'TEST_ECHO'
  TEST_MOCK_DATA                              = 'TEST_MOCK_DATA'


  def get_title(op):
    '''
      Get the display name for a given operation type.
    '''

    if not op in DbOp:
      raise ValueError()

    titles = {
      DbOp.UPGRADE_DATABASE:                            'Update the SQL database to the most recent schema',
      DbOp.CREATE_DATABASE_MIGRATION:                   'Create a new database migration, altering the schema',
      DbOp.DROP_AND_POPULATE_STRAINS:                   'Rebuild strain table from google sheet',
      DbOp.DROP_AND_POPULATE_WORMBASE_GENES:            'Rebuild wormbase gene table from external sources',
      DbOp.DROP_AND_POPULATE_STRAIN_ANNOTATED_VARIANTS: 'Rebuild Strain Annotated Variant table from .csv.gz file',
      DbOp.DROP_AND_POPULATE_PHENOTYPE_DB:              'Rebuild Phenotype Database table from datastore file records',
      DbOp.DROP_AND_POPULATE_PHENOTYPE_METADATA:        'Rebuild Phenotype Metadata table from datastore TraitFile entities',
      DbOp.DROP_AND_POPULATE_PHENOTYPES:                'Rebuild all Phenotype trait tables from datastore',
      DbOp.DROP_AND_POPULATE_ALL_TABLES:                'Rebuild All Tables',
      DbOp.POPULATE_PHENOTYPES_DATASTORE:               'Create / update datastore trait file records from Google Sheet',
      DbOp.TEST_ECHO:                                   'Test ETL - Echo',
      DbOp.TEST_MOCK_DATA:                              'Test ETL - Mock Data',
    }

    return titles.get(op, '???')
