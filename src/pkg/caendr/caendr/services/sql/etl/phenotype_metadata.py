import csv

from caendr.services.logger import logger

from caendr.models.datastore  import Species
from caendr.utils.local_files import LocalDatastoreFile


def parse_phenotype_metadata(species: Species, **files: LocalDatastoreFile):
  """
    Parsing function to load PhenotypeMetadata table from datastore.
    For bulk file ouputs each trait as a new row and replicates metadata for all of them
  """
  
  logger.info('Parsing function for traits metadata')
  
  for fname, fpath in files.items():

    # Get metadata for the file 
    md = fpath._metadata

    # If bulk file, open it and yield each trait as a new row with the file's metadata
    if md.is_bulk_file:
      with open(fpath) as csv_file:
        for idx, row in enumerate( csv.reader(csv_file, delimiter='\t') ):
          if idx == 0:
            continue
          else:
           trait_name = '_'.join(row[:3])
           yield {
             'trait_name':        trait_name,
             'species':           md.species.name,
             'description_short': md['description_short'],
             'description_long':  md['description_long'],
             'units':             md['units'],
             'doi':               md['doi'],
             'protocols':         md['protocols'],
             'source_lab':        md['source_lab'],
             'created_on':        md.created_on,
             'is_bulk_file':      md['is_bulk_file'],
            } 
    else:
        yield {
        'trait_name':        md['trait_name'],
        'species':           md.species.name,
        'description_short': md['description_short'],
        'description_long':  md['description_long'],
        'units':             md['units'],
        'doi':               md['doi'],
        'protocols':         md['protocols'],
        'source_lab':        md['source_lab'],
        'created_on':        md.created_on,
        'is_bulk_file':      md['is_bulk_file']
        }
