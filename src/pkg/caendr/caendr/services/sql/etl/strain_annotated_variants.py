import os
import csv
import re

from logzero import logger
from sqlalchemy.sql.expression import null



def parse_strain_variant_annotation_data(species, sva_fname: str):
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
  logger.info('Parsing extracted strain variant annotation .csv file')

  # Loop through each line in the CSV file, indexed
  with open(sva_fname) as csv_file:
    for idx, row in enumerate( csv.reader(csv_file, delimiter=',') ):

      # First line is column names - don't interpret as data
      if idx == 0:
        print(f'Column names are {", ".join(row)}')
        continue

      # If testing, finish early
      if os.getenv("USE_MOCK_DATA") and idx > 10:
        logger.warn("USE_MOCK_DATA Early Return!!!")
        return

      # Progress update
      if idx % 1000000 == 0:
        logger.debug(f"Processed {idx} lines")

      target_consequence = None
      consequence = row[4] if row[4] else None
      alt_target = re.match('^@[0-9]*$', consequence)
      if alt_target:
        target_consequence = int(consequence[1:])
        consequence = None

      # Yield the row as a dict
      yield {
        'id': idx,
        'chrom': row[0],
        'pos': int(row[1]) if row[1] else None,
        'ref_seq': row[2] if row[2] else None,
        'alt_seq': row[3] if row[3] else None,
        'consequence': consequence,
        'target_consequence': target_consequence,
        'gene_id': row[5] if (row[5] and row[5] != "NA") else None,
        'transcript': row[6] if row[6] else None,
        'biotype': row[7] if row[7] else None,

        # strand takes a single character in the SQL schema, and can be nullable. Convert R's NA to NULL
        'strand': row[8] if (row[8] and row[8] != "NA") else None,

        'amino_acid_change': row[9] if row[9] else None,
        'dna_change': row[10] if row[10] else None,
        'strains': row[11] if row[11] else None,
        'blosum': int(row[12]) if (row[12] and row[12] != "NA") else None,
        'grantham': int(row[13]) if (row[13] and row[13] != "NA") else None,
        'percent_protein': float(row[14]) if (row[14] and row[14] != "NA") else None,
        'gene': row[15] if row[15] else None,
        'variant_impact': row[16] if row[16] else None,
        'snpeff_impact': row[17] if row[17] else None,
        'divergent': True if row[18] == 'D' else False,
        'release': row[19] if row[19] else None
      }

  # In Python, loop vars maintain their final value after the loop ends
  print(f'Processed {idx} lines.')
