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
  
  for file_name, file_object in files.items():

    # Get metadata for the file 
    md = file_object.metadata
    tags = ', '.join(md['tags']) if md['tags'] is not None else None

    # If bulk file, open it and yield each trait as a new row with the file's metadata
    if md.is_bulk_file:
      with open(file_object) as csv_file:
        """
          Read the bulk file to generate the 'trait_name_caendr' and get 'wbgene_id'.

          Expected order of column headers:
          [ transcript    WormBaseGeneID     GeneName    AB1    BRC20067   BRC20263   .... (strains)]

          Concatenate 'transcript', 'WormBaseGeneID' and 'GeneName' with '_' to generate trait name.
        """
        for idx, row in enumerate( csv.reader(csv_file, delimiter='\t') ):
          if idx == 0:
            continue
          else:
           trait_name = '_'.join(row[:3])
           wbgene_id = row[1]
           yield {
             'trait_name_caendr':    trait_name,
             'trait_name_user':      md['trait_name_user'],
             'trait_name_display_1': trait_name,
             'trait_name_display_2': '',
             'trait_name_display_3': '',
             'species_name':         md.species.name,
             'wbgene_id':            wbgene_id,
             'description_short':    md['description_short'],
             'description_long':     md['description_long'],
             'units':                md['units'],
             'publication':          md['publication'],
             'protocols':            md['protocols'],
             'source_lab':           md['source_lab'],
             'institution':          md['institution'],
             'submitted_by':         md.get_user().full_name,
             'tags':                 tags,
             'capture_date':         md['capture_date'],
             'created_on':           md.created_on,
             'modified_on':          md.modified_on,
             'dataset':              md['dataset'],
             'is_bulk_file':         md['is_bulk_file'],
            } 
    else:
      yield {
      'trait_name_caendr':    md['trait_name_caendr'],
      'trait_name_user':      md['trait_name_user'],
      'trait_name_display_1': md['trait_name_display_1'],
      'trait_name_display_2': md['trait_name_display_2'],
      'trait_name_display_3': md['trait_name_display_3'],
      'species_name':         md.species.name,
      'wbgene_id':            'N/A',
      'description_short':    md['description_short'],
      'description_long':     md['description_long'],
      'units':                md['units'],
      'publication':          md['publication'],
      'protocols':            md['protocols'],
      'source_lab':           md['source_lab'],
      'institution':          md['institution'],
      'submitted_by':         md.get_user().full_name,
      'tags':                 tags,
      'capture_date':         md['capture_date'],
      'created_on':           md.created_on,
      'modified_on':          md.modified_on,
      'dataset':              md['dataset'],
      'is_bulk_file':         md['is_bulk_file'],
      }
