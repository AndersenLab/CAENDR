from typing import Dict

from caendr.utils.env              import get_env_var
from caendr.services.cloud.secret  import get_secret

# Local imports
from .strains                      import fetch_andersen_strains
from .wormbase                     import parse_gene_gtf, parse_gene_gff_summary
from .strain_annotated_variants    import parse_strain_variant_annotation_data

from caendr.models.sql             import Strain, WormbaseGeneSummary, WormbaseGene, StrainAnnotatedVariant
from caendr.models.datastore       import Species
from caendr.utils.local_files      import ForeignResourceWatcher, LocalDatastoreFileTemplate, GoogleSheetManager



# Bucket(s)
MODULE_DB_OPERATIONS_BUCKET_NAME = get_env_var('MODULE_DB_OPERATIONS_BUCKET_NAME')

# Filepaths
RELEASE_FILEPATH = get_env_var('MODULE_DB_OPERATIONS_RELEASE_FILEPATH', as_template=True)
SVA_FILEPATH     = get_env_var('MODULE_DB_OPERATIONS_SVA_FILEPATH',     as_template=True)

# Filenames
GENE_GFF_FILENAME = get_env_var('GENE_GFF_FILENAME',  as_template=True)
GENE_GTF_FILENAME = get_env_var('GENE_GTF_FILENAME',  as_template=True)
GENE_IDS_FILENAME = get_env_var('GENE_IDS_FILENAME',  as_template=True)
SVA_FILENAME      = get_env_var('SVA_CSVGZ_FILENAME', as_template=True)


# Get list of Google Sheet IDs for each species
# Expects secret names with prefix "ANDERSEN_LAB_STRAIN_SHEET_" and species ID in all caps
ANDERSEN_LAB_STRAIN_SHEETS = {
  species_name: get_secret(f'ANDERSEN_LAB_STRAIN_SHEET_{species_name.upper()}')
    for species_name in Species.all()
}



#
# Class definition
#

class TableConfig():
  '''
    Bundle together configuration objects / functions for building a single SQL table.
  '''

  def __init__(self, table, parse, files: Dict[str, ForeignResourceWatcher]):
    self.table = table
    self.parse = parse
    self.files = files


  @property
  def table_name(self):
    '''
      The name of the SQL table.
    '''
    return self.table.__tablename__


  #
  # Fetching
  #

  def fetch_files_for_species(self, species):
    '''
      Fetch all the files required for this species from the database.
    '''
    return {
      file_id: file_template.get_for_species(species)
        for file_id, file_template in self.files.items()
        if file_template.has_for_species(species)
    }


  #
  # Parsing
  #

  def parse_for_species(self, species):
    '''
      Apply this TableConfig's parse function to its set of files,
      yielding the results as a generator.
    '''
    return self.parse(species, **self.fetch_files_for_species(species), start_idx=self.table.query.count())



#
# Specific table objects
#

StrainConfig = TableConfig(
    table = Strain,
    parse = fetch_andersen_strains,
    files = {
      'STRAINS': GoogleSheetManager( 'STRAINS', ANDERSEN_LAB_STRAIN_SHEETS ),
    },
)

WormbaseGeneSummaryConfig = TableConfig(
  table = WormbaseGeneSummary,
  parse = parse_gene_gff_summary,
  files = {
    'GENE_GFF': LocalDatastoreFileTemplate( 'GENE_GFF', MODULE_DB_OPERATIONS_BUCKET_NAME, RELEASE_FILEPATH, GENE_GFF_FILENAME ),
  },
)

WormbaseGeneConfig = TableConfig(
  table = WormbaseGene,
  parse = parse_gene_gtf,
  files = {
    'GENE_GTF': LocalDatastoreFileTemplate( 'GENE_GFF', MODULE_DB_OPERATIONS_BUCKET_NAME, RELEASE_FILEPATH, GENE_GTF_FILENAME ),
    'GENE_IDS': LocalDatastoreFileTemplate( 'GENE_GFF', MODULE_DB_OPERATIONS_BUCKET_NAME, RELEASE_FILEPATH, GENE_IDS_FILENAME ),
  },
)

StrainAnnotatedVariantConfig = TableConfig(
  table = StrainAnnotatedVariant,
  parse = parse_strain_variant_annotation_data,
  files = {
    'SVA_CSVGZ': LocalDatastoreFileTemplate( 'SVA_CSVGZ', MODULE_DB_OPERATIONS_BUCKET_NAME, SVA_FILEPATH, SVA_FILENAME ),
  },
)
