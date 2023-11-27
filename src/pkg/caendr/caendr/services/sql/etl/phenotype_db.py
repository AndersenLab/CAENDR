from caendr.services.logger import logger

from caendr.models.datastore  import Species
from caendr.utils.local_files import LocalDatastoreFile
from caendr.utils.data        import log_status



@log_status(1000, mock_data_size=100)
def parse_phenotypedb_traits_data(species: Species, **files: LocalDatastoreFile):
  """
    Parsing function for trait files that follow the outlined structure:
      - the first row of the table are the headers that represent trait names
      - the following rows are strain names with corresponding trait values

    Sample table structure:
    [
      strain          length_2_4_D         length_Abamectin
      AB1             25.2394870867178     7.54101506066384
      BRC20263        -91.45616678         101.231626695727
      CB4855          7.91667625972722     49.9315541104696
    ]  
  """
  
  logger.info('Parsing extracted phenotype database TSV file(s)')

  # Loop through each line in each file, indexed
  for file_name, local_file in files.items():
    for idx, row in enumerate( local_file ):

        # First line is column names - don't interpret as data
        if idx == 0:
          logger.info(f'Column names in file "{file_name}" are: {", ".join(row)}')
          column_header_map = { name: idx for idx, name in enumerate(row) }
          continue

        # Get trait value for each strain
        strain_name = row[0]
        for header in column_header_map:
          if column_header_map[header] == 0:
            continue
          trait_name = header
          trait_value = row[column_header_map[header]]

          # Skip the rows with "NA" trait values
          if trait_value == 'NA':
            continue

          # Yield each trait measurement as a new row
          yield {
            'trait_name':   trait_name,
            'strain_name':  strain_name,
            'trait_value':  trait_value
          }



@log_status(10000, mock_data_size=100)
def parse_phenotypedb_bulk_trait_file(species: Species, **files: LocalDatastoreFile):
  """
      Parsing function for Zhang Gene Expression traits file. 
      The first 3 columns of the first row are expected to be ['transcript', 'WormBaseGeneID', 'GeneName']
      The rest of the column headers are the strain names.
      Each row represents trait value for corresponding strain.
  """

  logger.info('Parsing extracted phenotype database bulk TSV file(s)')

  # Loop through each line in each file, indexed
  for file_name, local_file in files.items():
    for idx, row in enumerate( local_file ):

        # First line is column names - don't interpret as data
        if idx == 0:
          logger.info(f'Column names in file "{file_name}" are: {", ".join(row)}')
          column_header_map = { name: idx for idx, name in enumerate(row) }
          continue

        # Generate trait_name joining 'transcript', 'WormBaseGeneID' and 'GeneName'
        trait_name = '_'.join(row[:3])
        for header, idx in column_header_map.items():

          # Skip the first 3 columns, which are trait descriptions
          if idx in (0, 1, 2):
            continue

          # Get trait value for each strain
          strain_name = header
          trait_value = row[column_header_map[header]]

          # Skip if trait_value is 'NA'
          if trait_value == 'NA':
            continue

          # Yield each trait measurement as a new row
          yield {
            'trait_name':   trait_name,
            'strain_name':  strain_name,
            'trait_value':  trait_value
          }
