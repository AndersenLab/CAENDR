import os
import csv
import gzip
import re

from caendr.services.logger import logger

from caendr.models.datastore  import Species
from caendr.utils.local_files import LocalDatastoreFile
from caendr.models.sql import Variant


def parse_variant_data(species: Species, **files: LocalDatastoreFile):

  logger.info(f'Parsing variant CSV file')

  for file_name, file_path in files.items():
    column_header_map = {}

    # Loop through each line in the CSV file, indexed
    with gzip.open(file_path, mode='rt') as csv_file:
      for idx, row in enumerate( csv.reader(csv_file, delimiter=',') ):

        # First line is column names - don't interpret as data
        # Create dict from header column names to row indices
        if idx == 0:
          logger.info(f'Column names in file "{file_name}" are: {", ".join(row)}')
          column_header_map = { name.lower(): idx for idx, name in enumerate(row) }
          continue

        # If testing, finish early
        if os.getenv("USE_MOCK_DATA") and idx > 1000000:
          logger.warn("USE_MOCK_DATA Early Return!!!")
          return

        # Progress update
        if idx % 1000000 == 0:
          logger.debug(f"Processed {idx} lines")

        # Map row to dict, using file headers as keys
        row = {
          header: row[column_header_map[header]] for header in column_header_map
        }

        divergent = row.get('hdr')
        if divergent is not None:
          divergent = divergent == 'YES'
          
        # Yield the row as a dict
        yield {

          # These two fields form the primary key, i.e. the combination of both must be unique within the table
          'species_name':       species.name,

          'chrom':              row['chrom'],
          'pos':                get_row(row, 'pos', map=int),
          'ref_seq':            row.get('ref'),
          'alt_seq':            row.get('alt'),
          'strains':            row.get('strain'),
          'divergent':          divergent,
          'release':            species.release_sva,
        }

    # In Python, loop vars maintain their final value after the loop ends
    print(f'Processed {idx} lines total for {file_name} {species.name}')



def parse_annovar_variant_annotation_data(species: Species, **files: LocalDatastoreFile):

  logger.info(f'Parsing extracted Annovar variant annotation CSV file')

  # Get dict of variant IDs {(chrom, pos): variant_id}
  variant_dict = Variant.query_all(species=species)

  for file_name, file_path in files.items():
    column_header_map = {}

    # Loop through each line in the CSV file, indexed
    with gzip.open(file_path, mode='rt') as csv_file:
      for idx, row in enumerate( csv.reader(csv_file, delimiter=',') ):

        # First line is column names - don't interpret as data
        # Create dict from header column names to row indices
        if idx == 0:
          logger.info(f'Column names in file "{file_name}" are: {", ".join(row)}')
          column_header_map = { name.lower(): idx for idx, name in enumerate(row) }
          continue

        # If testing, finish early
        if os.getenv("USE_MOCK_DATA") and idx > 1000000:
          logger.warn("USE_MOCK_DATA Early Return!!!")
          return

        # Progress update
        if idx % 1000000 == 0:
          logger.debug(f"Processed {idx} lines")

        # Map row to dict, using file headers as keys
        row = {
          header: row[column_header_map[header]] for header in column_header_map
        }

        # Get variant_id
        row['variant_id'] = variant_dict[(row['chrom'], get_row(row, 'pos', map=int))]

        # Yield the row as a dict
        yield {

          # These two fields form the primary key, i.e. the combination of both must be unique within the table
          'variant_id':         row.get('variant_id'),
          'consequence':        row.get('consequence'),
          'gene_id':            get_row(row, 'wbgene', nullable=True),
          'transcript':         row.get('transcript_name'),

          'amino_acid_change':  row.get('aa')[2:],
          'blosum':             get_row(row, 'blosum', nullable=True, map=int),
          'grantham':           get_row(row, 'grantham', nullable=True, map=int),
          'percent_protein':    get_row(row, 'percent_protein', nullable=True, map=float),
          'gene':               row.get('gene_name'),
          'variant_impact':     row.get('impact'),
        }

    # In Python, loop vars maintain their final value after the loop ends
    print(f'Processed {idx} lines total for {file_name} {species.name}')


def parse_csq_variant_annotation_data(species: Species, **files: LocalDatastoreFile):
  logger.info(f'Parsing extracted CSQ variant annotation CSV file')

  # Get dict of variant IDs {(chrom, pos): variant_id}
  variant_dict = Variant.query_all(species=species)

  for file_name, file_path in files.items():
    column_header_map = {}

    # Loop through each line in the CSV file, indexed
    with gzip.open(file_path, mode='rt') as csv_file:
      for idx, row in enumerate( csv.reader(csv_file, delimiter=',') ):

        # First line is column names - don't interpret as data
        # Create dict from header column names to row indices
        if idx == 0:
          logger.info(f'Column names in file "{file_name}" are: {", ".join(row)}')
          column_header_map = { name.lower(): idx for idx, name in enumerate(row) }
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
        consequence = row.get('consequence')
        alt_target = re.match('^@[0-9]*$', consequence)
        if alt_target:
          target_consequence = int(consequence[1:])
          consequence = None

        # Get variant_id
        row['variant_id'] = variant_dict[(row['chrom'], get_row(row, 'pos', map=int))]

        # Yield the row as a dict
        yield {

          # These two fields form the primary key, i.e. the combination of both must be unique within the table
          'variant_id':         row.get('variant_id'),
          'consequence':        consequence,
          'target_consequence': target_consequence,
          'gene_id':            get_row(row, 'wbgene', nullable=True),
          'transcript':         row.get('transcript_name'),

          'amino_acid_change':  row.get('aa'),
          'dna_change':         row.get('dnachange'),
          'blosum':             get_row(row, 'blosum', nullable=True, map=int),
          'grantham':           get_row(row, 'grantham', nullable=True, map=int),
          'percent_protein':    get_row(row, 'percent_protein', nullable=True, map=float),
          'gene':               row.get('gene_name'),
        }

    # In Python, loop vars maintain their final value after the loop ends
    print(f'Processed {idx} lines total for {file_name} {species.name}')


def parse_vep_variant_annotation_data(species: Species, **files: LocalDatastoreFile):
  logger.info(f'Parsing extracted VEP variant annotation CSV file')

  # Get dict of variant IDs {(chrom, pos): variant_id}
  variant_dict = Variant.query_all(species=species)

  for file_name, file_path in files.items():
    column_header_map = {}

    # Loop through each line in the CSV file, indexed
    with gzip.open(file_path, mode='rt') as csv_file:
      for idx, row in enumerate( csv.reader(csv_file, delimiter=',') ):

        # First line is column names - don't interpret as data
        # Create dict from header column names to row indices
        if idx == 0:
          logger.info(f'Column names in file "{file_name}" are: {", ".join(row)}')
          column_header_map = { name.lower(): idx for idx, name in enumerate(row) }
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

        # Get variant_id
        row['variant_id'] = variant_dict[(row['chrom'], get_row(row, 'pos', map=int))]

        # Yield the row as a dict
        yield {

          # These two fields form the primary key, i.e. the combination of both must be unique within the table
          'variant_id':         row.get('variant_id'),
          'consequence':        row.get('consequence'),
          'gene_id':            get_row(row, 'wbgene', nullable=True),
          'transcript':         row.get('transcript_name'),

          'amino_acid_change':  row.get('aa'),
          'blosum':             get_row(row, 'blosum', nullable=True, map=int),
          'grantham':           get_row(row, 'grantham', nullable=True, map=int),
          'percent_protein':    get_row(row, 'percent_protein', nullable=True, map=float),
          'gene':               row.get('gene_name'),
          'variant_impact':     row.get('impact'),
        }

    # In Python, loop vars maintain their final value after the loop ends
    print(f'Processed {idx} lines total for {file_name} {species.name}')


def parse_snpeff_variant_annotation_data(species: Species, **files: LocalDatastoreFile):
  logger.info(f'Parsing extracted SnpEff variant annotation CSV file')

  # Get dict of variant IDs {(chrom, pos): variant_id}
  variant_dict = Variant.query_all(species=species)

  for file_name, file_path in files.items():
    column_header_map = {}

    # Loop through each line in the CSV file, indexed
    with gzip.open(file_path, mode='rt') as csv_file:
      for idx, row in enumerate( csv.reader(csv_file, delimiter=',') ):

        # First line is column names - don't interpret as data
        # Create dict from header column names to row indices
        if idx == 0:
          logger.info(f'Column names in file "{file_name}" are: {", ".join(row)}')
          column_header_map = { name.lower(): idx for idx, name in enumerate(row) }
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

        consequence = row.get('consequence')

        # Get variant_id
        row['variant_id'] = variant_dict[(row['chrom'], get_row(row, 'pos', map=int))]

        # Yield the row as a dict
        yield {

          # These two fields form the primary key, i.e. the combination of both must be unique within the table
          'variant_id':         row.get('variant_id'),
          'consequence':        consequence,
          'gene_id':            get_row(row, 'wbgene', nullable=True),
          'transcript':         row.get('transcript_name'),

          'amino_acid_change':  row.get('aa'),
          'grantham':           get_row(row, 'grantham',  nullable=True, map=int),
          'percent_protein':    get_row(row, 'percent_protein', nullable=True, map=float),
          'gene':               row.get('gene_name'),
          'variant_impact':     row.get('impact'),
        }

    # In Python, loop vars maintain their final value after the loop ends
    print(f'Processed {idx} lines total for {file_name} {species.name}')


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
  if val is None or (nullable and (val == 'NA' or val == 'N/A')):
    return None

  # If mapping function provided and val exists, apply it
  if map is not None:
    return map(val)

  return val

