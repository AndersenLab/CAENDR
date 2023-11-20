import csv


from caendr.services.logger import logger
from sqlalchemy.sql.expression import null



def parse_phenotypedb_traits_data(species, *fnames: str):
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

  # Loop through each line in each TSV file, indexed
  for fname in fnames:
    with open(fname) as csv_file:
      for idx, row in enumerate( csv.reader(csv_file, delimiter='\t') ):

        # First line is column names - don't interpret as data
        if idx == 0:
          logger.info(f'Column names in file "{fname}" are: {", ".join(row)}')
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
            'strain':       strain_name,
            'trait_value':  trait_value
          }


  # In Python, loop vars maintain their final value after the loop ends
  print(f'Processed {idx} lines total for {species.name}')
