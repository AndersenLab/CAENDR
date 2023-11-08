import os
import csv
import gzip
import re

from caendr.services.logger import logger
from sqlalchemy.sql.expression import null



# TODO: Write a parsing function for the phenotype file(s)
#       You should get the list of filenames as a list of strings
#       (Don't worry about start_idx)

def parse_strain_variant_annotation_data(species, *fnames: str, start_idx = 0):
  logger.info('Parsing extracted phenotype database TSV file(s)')

  # Loop through each line in each TSV file, indexed
  for fname in fnames:
    with gzip.open(fname, mode='rt') as csv_file:
      for idx, row in enumerate( csv.reader(csv_file, delimiter='\t') ):

        # First line is column names - don't interpret as data
        # TODO: Create some data structure that lets you map a column index to a strain name
        #       Hint -- I think you could just save the strains as a list, and zip each data row with that list
        if idx == 0:
          logger.info(f'Column names in file "{fname}" are: {", ".join(row)}')

          # column_header_map = { name: idx for idx, name in enumerate(row) }
          continue

        # If testing, finish early
        if os.getenv("USE_MOCK_DATA") and idx > 10:
          logger.warn("USE_MOCK_DATA Early Return!!!")
          return

        # Progress update
        if idx % 1000000 == 0:
          logger.debug(f"Processed {idx} lines")

        # TODO: Any processing required for this line

        # TODO: Yield a *single* row as a dict
        #       This might have to go in a loop, to yield each trait measurement as a new row?
        yield {}

  # In Python, loop vars maintain their final value after the loop ends
  print(f'Processed {idx} lines total for {species.name}')
