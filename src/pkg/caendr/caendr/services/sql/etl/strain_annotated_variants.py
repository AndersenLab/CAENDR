import os
import csv
import re

from caendr.services.logger import logger
from sqlalchemy.sql.expression import null



def parse_strain_variant_annotation_data(species, sva_fname: str, start_idx = 0):
  """
      Load strain variant annotation table data:

      CHROM,POS,REF,ALT,CONSEQUENCE,WORMBASE_ID,TRANSCRIPT,BIOTYPE,
      STRAND,AMINO_ACID_CHANGE,DNA_CHANGE,Strains,BLOSUM,Grantham,
      Percent_Protein,GENE,VARIANT_IMPACT,SNPEFF_IMPACT,DIVERGENT,RELEASE

      Expected sample headers/rows format:
        Headers:
          [
            "CHROM",       "POS",            "REF",           "ALT",       "CONSEQUENCE",
            "WORMBASE_ID", "TRANSCRIPT",     "BIOTYPE",       "STRAND",    "AMINO_ACID_CHANGE",
            "DNA_CHANGE",  "Strains",        "BLOSUM",        "Grantham",  "Percent_Protein",
            "GENE",        "VARIANT_IMPACT", "SNPEFF_IMPACT", "DIVERGENT", "RELEASE"
          ]
        Rows:
          ["I",3782,"G","A",NA,NA,NA,NA,NA,NA,NA,"",NA,NA,NA,NA,NA,NA,NA,NA]

  """
  logger.info('Parsing extracted strain variant annotation TSV file')

  column_header_map = {}

  # Loop through each line in the CSV file, indexed
  with open(sva_fname) as csv_file:
    for idx, row in enumerate( csv.reader(csv_file, delimiter='\t') ):

      # First line is column names - don't interpret as data
      # Create dict from header column names to row indices
      if idx == 0:
        logger.info(f'Column names in file "{sva_fname}" are: {", ".join(row)}')
        column_header_map = { name: idx for idx, name in enumerate(row) }
        continue

      # If testing, finish early
      if os.getenv("USE_MOCK_DATA") and idx > 10:
        logger.warn("USE_MOCK_DATA Early Return!!!")
        return

      # Progress update
      if idx % 1000000 == 0:
        logger.debug(f"Processed {idx} lines")

      # Map row to dict, using file headers as keys
      row = {
        header: row[column_header_map[header]] for header in column_header_map
      }

      target_consequence = None
      consequence = row.get('CONSEQUENCE')
      alt_target = re.match('^@[0-9]*$', consequence)
      if alt_target:
        target_consequence = int(consequence[1:])
        consequence = None

      # Yield the row as a dict
      yield {
        'id':                 start_idx + idx,
        'species_name':       species.name,
        'chrom':              row['CHROM'],
        'pos':                get_row(row, 'POS', map=int),
        'ref_seq':            row.get('REF'),
        'alt_seq':            row.get('ALT'),
        'consequence':        consequence,
        'target_consequence': target_consequence,
        'gene_id':            get_row(row, 'WORMBASE_ID', nullable=True),
        'transcript':         row.get('TRANSCRIPT'),
        'biotype':            row.get('BIOTYPE'),

        # strand takes a single character in the SQL schema, and can be nullable. Convert R's NA to NULL
        'strand':             get_row(row, 'STRAND', nullable=True),

        'amino_acid_change':  row.get('AMINO_ACID_CHANGE'),
        'dna_change':         row.get('DNA_CHANGE'),
        'strains':            row.get('Strains'),
        'blosum':             get_row(row, 'BLOSUM',          nullable=True, map=int),
        'grantham':           get_row(row, 'Grantham',        nullable=True, map=int),
        'percent_protein':    get_row(row, 'Percent_Protein', nullable=True, map=float),
        'gene':               row.get('GENE'),
        'variant_impact':     row.get('VARIANT_IMPACT'),
        'divergent':          row.get('DIVERGENT') == 'D',
        'release':            row.get('RELEASE'),
      }

  # In Python, loop vars maintain their final value after the loop ends
  print(f'Processed {idx} lines.')


def get_row(row, key, nullable=False, map=None):
  '''
    Get a column value from a row.

    Arguments:
      row (dict): The row as a dict.
      key: The key to lookup in the row.
      nullable (bool): Whether values in this row can be null ('NA'). Converts null values to None.
      map (func): A mapping function to apply to all non-null values.
  '''
  val = row.get(key)

  # Return early if value is null
  # Maps R's 'NA' value to None, if applicable
  if val is None or (nullable and val == 'NA'):
    return None

  # If mapping function provided and val exists, apply it
  if map is not None:
    return map(val)

  return val
