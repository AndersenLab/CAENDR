import csv


from caendr.services.logger import logger
from sqlalchemy.sql.expression import null



def parse_phenotypedb_traits_data(species, **files):
  """
    Parsing function for trait files that follow the outlined structure:
    - row 1 represents the headers of the table, where:
      - the first value is the header of the first column (expected 'trait_name')
      - the following values are the strain names (expected 'AB1', 'BRC20263', 'CB4855')
    - rows 2 - end are the body of the table, where:
      - first value of each row represents trait names (expected 'length_2_4_D', 'length_Abamectin')
      - the following values represent trait values for each corresponding strain (expected '25.2394870867178', '7.54101506066384', '7.91667625972722')

    TL;DR 
    Table structure:
    [
      trait_name           AB1                BRC20263            CB4855
      length_2_4_D         25.2394870867178   7.54101506066384    7.91667625972722
      length_Abamectin     -91.45616678       101.231626695727    49.9315541104696
    ]
  """
  
  logger.info('Parsing extracted phenotype database TSV file(s)')

  # Loop through each line in each file, indexed
  for file_name, file_path in files.items():
    with open(file_path) as csv_file:
      for idx, row in enumerate( csv.reader(csv_file, delimiter='\t') ):

        # First line is column names - don't interpret as data
        if idx == 0:
          logger.info(f'Column names in file "{file_name}" are: {", ".join(row)}')
          column_header_map = { name: idx for idx, name in enumerate(row) }
          continue

        # Progress update
        if idx % 1000000 == 0:
          logger.debug(f"Processed {idx} lines")

        # Get trait value for each strain
        trait_name = row[0]
        for header in column_header_map:
          if column_header_map[header] == 0:
            continue
          strain_name = header
          trait_value = row[column_header_map[header]]

          # Yield each trait measurement as a new row
          yield {
            'trait_name':   trait_name,
            'strain_name':  strain_name,
            'trait_value':  trait_value
          }


  # In Python, loop vars maintain their final value after the loop ends
  print(f'Processed {idx} lines total for {species.name}')


def parse_phenotypedb_bulk_trait_file(species, **files):
  """
      Parsing function for Zhang Gene Expression traits file. 
      The first 3 columns of the first row are expected to be ['transcript', 'WormBaseGeneID', 'GeneName']
      The rest of the column headers are the strain names.
      Each row represents trait value for corresponding strain.
  """

  logger.info('Parsing extracted phenotype database bulk TSV file(s)')

    # Loop through each line in each file, indexed
  for file_name, file_path in files.items():
    with open(file_path) as csv_file:
      for idx, row in enumerate( csv.reader(csv_file, delimiter='\t') ):

        # First line is column names - don't interpret as data
        if idx == 0:
          logger.info(f'Column names in file "{file_name}" are: {", ".join(row)}')
          column_header_map = { name: idx for idx, name in enumerate(row) }
          continue

        # Progress update
        if idx % 1000000 == 0:
          logger.debug(f"Processed {idx} lines")

        # Generate trait_name joining 'transcript', 'WormBaseGeneID' and 'GeneName'
        trait_name = '_'.join(row[:3])
        for header, idx in column_header_map.items():

          # Skip the first 3 columns, which are trait descriptions
          if idx in (0, 1, 2):
            continue

          # Get trait value for each strain
          strain_name = header
          trait_value = row[column_header_map[header]]

          # Yield each trait measurement as a new row
          yield {
            'trait_name':   trait_name,
            'strain_name':  strain_name,
            'trait_value':  trait_value
          }




def parse_single_trait_file(species, *fnames: str):
  """
    Parsing function for single trait files.
    The first row of the table serves as the headers (expected: 'Strain', TRAIT_NAME).
    The following rows are strain names with corresponding trait values

    Expected sample structure of files:
    [
      Strain       Carbaryl_length
      AB1          6.26348038596805
      BRC20263     -8.24506908772116
      CB4854       6.03000802518469
    ]
  """

  logger.info('Parsing extracted phenotype database single trait TSV file(s)')

  # Loop through each line in each TSV file, indexed
  for fname in fnames:
    with open(fname) as csv_file:
      for idx, row in enumerate( csv.reader(csv_file, delimiter='\t') ):

        # Get trait name from the first line of the table
        if idx == 0:
          trait_name = row[1]
          continue
        
        # Progress update
        if idx % 1000000 == 0:
          logger.debug(f"Processed {idx} lines")

        #  Yield each row as an object
        yield {
          'trait_name': trait_name,
          'strain': row[0],
          'trait_value': row[1],
        }
