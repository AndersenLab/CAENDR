import os
import csv
import re
import gzip
import shutil

from logzero import logger
from sqlalchemy.sql.expression import null

from caendr.models.sql import StrainAnnotatedVariant


def load_strain_annotated_variants(db, sva_fname: str):
  logger.info('Loading strain variant annotated csv')
  sva_data = fetch_strain_variant_annotation_data(sva_fname)
  logger.info('Inserting strain annotated variant data into database')
  db.session.bulk_insert_mappings(StrainAnnotatedVariant, sva_data)
  db.session.commit()
  logger.info(f'Inserted {StrainAnnotatedVariant.query.count()} Strain Annotated Variants')


def fetch_strain_variant_annotation_data(sva_gz_fname: str):
  """
      Load strain variant annotation table data:

      CHROM,POS,REF,ALT,CONSEQUENCE,WORMBASE_ID,TRANSCRIPT,BIOTYPE,
      STRAND,AMINO_ACID_CHANGE,DNA_CHANGE,Strains,BLOSUM,Grantham,
      Percent_Protein,GENE,VARIANT_IMPACT,DIVERGENT

  """
  logger.info('Extracting strain variant annotation .csv.gz file')
  sva_fname = 'sva.csv'
  with gzip.open(sva_gz_fname, 'rb') as f_in:
    with open(sva_fname, 'wb') as f_out:
      shutil.copyfileobj(f_in, f_out)
  
  logger.info('Parsing extracted strain variant annotation .csv file')
  with open(sva_fname) as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=',')

    line_count = -1
    for row in csv_reader:
      if line_count == -1:
        print(f'Column names are {", ".join(row)}')
        line_count += 1
      else:
        line_count += 1
        if os.getenv("USE_MOCK_DATA") and line_count > 10:
          logger.warn("USE_MOCK_DATA Early Return!!!")    
          return    
        if line_count % 1000000 == 0:
          logger.debug(f"Processed {line_count} lines")

        # expected sample headers/rows format
        # Headers:
        # ["","CHROM","POS","REF","ALT","CONSEQUENCE","WORMBASE_ID","TRANSCRIPT","BIOTYPE","STRAND","AMINO_ACID_CHANGE","DNA_CHANGE","Strains","BLOSUM","Grantham","Percent_Protein","GENE","VARIANT_IMPACT","SNPEFF_IMPACT","DIVERGENT"]
        # Rows:
        # ["1","I",3782,"G","A",NA,NA,NA,NA,NA,NA,NA,"",NA,NA,NA,NA,NA,NA,NA]
        #
        # The literal indexes below for row[N] are off-by-one from the CSV
        # remove the first element from the row.
        row.pop(0)

        target_consequence = None
        consequence = row[4] if row[4] else None
        pattern = '^@[0-9]*$'
        alt_target = re.match(pattern, consequence)
        if alt_target:
          target_consequence = int(consequence[1:])
          consequence = None

        # strand takes a single character in the SQL schema, and can be nullable. Convert R's NA to NULL
        strand = None if (not row[8] or row[8] == "NA") else row[8]

        data = {
          'id': line_count,
          'chrom': row[0],
          'pos': int(row[1]),
          'ref_seq': row[2] if row[2] else None,
          'alt_seq': row[3] if row[3] else None,
          'consequence': consequence,
          'target_consequence': target_consequence,
          'gene_id': row[5] if (row[5] and row[5] != "NA") else None,
          'transcript': row[6] if row[6] else None,
          'biotype': row[7] if row[7] else None,
          'strand': strand,
          'amino_acid_change': row[9] if row[9] else None,
          'dna_change': row[10] if row[10] else None,
          'strains': row[11] if row[11] else None,
          'blosum': int(row[12]) if (row[12] and row[12] != "NA") else None,
          'grantham': int(row[13]) if (row[13] and row[13] != "NA") else None,
          'percent_protein': float(row[14]) if (row[14] and row[14] != "NA") else None,
          'gene': row[15] if row[15] else None,
          'variant_impact': row[16] if row[16] else None,
          'divergent': True if row[17] == 'D' else False,
        }
        
        yield data

  print(f'Processed {line_count} lines.')
