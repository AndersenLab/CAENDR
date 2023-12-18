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
             'trait_name_caendr': trait_name,
             'trait_name_user':   md['trait_name_user'],
             'species':           md.species.name,
             'wbgene_id':         row[1],
             'description_short': md['description_short'],
             'description_long':  md['description_long'],
             'units':             md['units'],
             'publication':       md['publication'],
             'protocols':         md['protocols'],
             'source_lab':        md['source_lab'],
             'institution':       md['institution'],
             'tags':              md['tags'],
             'capture_date':      md['capture_date'],
             'created_on':        md.created_on,
             'modified_on':       md.modified_on,
             'dataset':           md['dataset'],
             'is_bulk_file':      md['is_bulk_file'],
            } 
    else:
      yield {
      'trait_name_caendr': md['trait_name_caendr'],
      'trait_name_user':   md['trait_name_user'],
      'species':           md.species.name,
      'wbgene_id':         'N/A',
      'description_short': md['description_short'],
      'description_long':  md['description_long'],
      'units':             md['units'],
      'publication':       md['publication'],
      'protocols':         md['protocols'],
      'source_lab':        md['source_lab'],
      'institution':       md['institution'],
      'tags':              md['tags'],
      'capture_date':      md['capture_date'],
      'created_on':        md.created_on,
      'modified_on':       md.modified_on,
      'dataset':           md['dataset'],
      'is_bulk_file':      md['is_bulk_file'],
      }
