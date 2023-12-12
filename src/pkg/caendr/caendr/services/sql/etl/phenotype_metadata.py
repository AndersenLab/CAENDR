import csv

from caendr.services.logger import logger

from caendr.models.datastore  import Species
from caendr.utils.local_files import LocalDatastoreFile


def parse_phenotype_metadata(species: Species, **files: LocalDatastoreFile):

  
  logger.info('Parsing function for traits metadata')
  
  for fname, fpath in files.items():

    # Get metadata for the file 
    md = fpath._metadata

    # If bulk file, open it and yield each trait as a new row with the file's metadata
    # if md.is_bulk_file:
    #   with open(fpath) as csv_file:
    #     for idx, row in enumerate( csv.reader(csv_file, delimiter='\t') ):
    #       if idx == 0:
    #         continue
    #       else:
    #        trait_name = '_'.join(row[:3])
    #        yield {
    #          'trait_name':        trait_name,
    #          'species':           md._get_raw_prop('species'),
    #          'description_short': md._get_raw_prop('description_short'),
    #          'description_long':  md._get_raw_prop('description_long'),
    #          'units':             md._get_raw_prop('units'),
    #          'doi':               md._get_raw_prop('doi'),
    #          'protocols':         md._get_raw_prop('protocols'),
    #          'source_lab':        md._get_raw_prop('source_lab'),
    #          'created_on':        md._get_raw_prop('created_on')
    #         } 
    # else:
    yield {
    'trait_name':        md._get_raw_prop('trait_name'),
    'species':           md._get_raw_prop('species'),
    'description_short': md._get_raw_prop('description_short'),
    'description_long':  md._get_raw_prop('description_long'),
    'units':             md._get_raw_prop('units'),
    'doi':               md._get_raw_prop('doi'),
    'protocols':         md._get_raw_prop('protocols'),
    'source_lab':        md._get_raw_prop('source_lab'),
    'created_on':        md._get_raw_prop('created_on')
    }
