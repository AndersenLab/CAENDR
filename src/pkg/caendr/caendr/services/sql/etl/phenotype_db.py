import os
import csv
import gzip
import re

from caendr.services.logger import logger
from sqlalchemy.sql.expression import null



def parse_phenotypedb_traits_data(species, *fnames: str):
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
