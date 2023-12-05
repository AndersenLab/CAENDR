from typing import Dict, List

from caendr.utils.env              import get_env_var
from caendr.services.cloud.secret  import get_secret

# Local imports
from .strains                      import fetch_andersen_strains
from .wormbase                     import parse_gene_gtf, parse_gene_gff_summary
from .strain_annotated_variants    import parse_strain_variant_annotation_data
from .phenotype_db                 import parse_phenotypedb_traits_data, parse_phenotypedb_bulk_trait_file

from caendr.models.sql             import Strain, WormbaseGeneSummary, WormbaseGene, StrainAnnotatedVariant, PhenotypeDatabase
from caendr.models.datastore       import Species, TraitFile
from caendr.services.cloud.storage import BlobURISchema
from caendr.models.datastore       import Species
from caendr.utils.local_files      import ForeignResource, ForeignResourceTemplate, LocalDatastoreFileTemplate, LocalGoogleSheetTemplate



# Bucket(s)
MODULE_DB_OPERATIONS_BUCKET_NAME = get_env_var('MODULE_DB_OPERATIONS_BUCKET_NAME')

# Filepaths
RELEASE_FILEPATH   = get_env_var('MODULE_DB_OPERATIONS_RELEASE_FILEPATH', as_template=True)
SVA_FILEPATH       = get_env_var('MODULE_DB_OPERATIONS_SVA_FILEPATH',     as_template=True)
PHENOTYPE_FILEPATH = get_env_var('MODULE_DB_OPERATIONS_PHENOTYPE_FILEPATH', as_template=True)

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
# Helper class definition
#

class ParseConfig():
  '''
    Helper class to associate a parsing function with a set of files.
  '''

  def __init__(self, parse, *files: ForeignResourceTemplate):
    self.parse = parse
    self.files = files


  def fetch_all(self, species) -> Dict[str, ForeignResource]:
    '''
      Fetch all the files required for this species.
    '''
    return {
      file_template.resource_id: file_template.get_for_species(species).fetch()
        for file_template in self.files
        if  file_template.has_for_species(species)
    }


  def parse_all(self, species):
    '''
      Apply this object's parse function to its set of files, yielding the results as a generator.
    '''
    return self.parse(species, **self.fetch_all(species))



#
# Primary class definition
#

class TableConfig():
  '''
    Bundle together configuration objects / functions for building a single SQL table.
  '''

  def __init__(self, table, *parse_configs: ParseConfig):
    self.table = table
    self._parse_configs = parse_configs


  @property
  def table_name(self):
    '''
      The name of the SQL table.
    '''
    return self.table.__tablename__

  @property
  def all_resources(self) -> List[ForeignResourceTemplate]:
    resources = []
    for config in self._parse_configs:
      resources += config.files
    return resources


  def parse_for_species(self, species):
    '''
      Apply all parsing functions in this config to their associated files,
      yielding from each set in sequence.
    '''
    for config in self._parse_configs:
      yield from config.parse_all(species)



#
# Specific table objects
#

StrainConfig = TableConfig(
  Strain,
  ParseConfig(
    fetch_andersen_strains,
    LocalGoogleSheetTemplate( 'STRAINS', ANDERSEN_LAB_STRAIN_SHEETS ),
  ),
)

WormbaseGeneSummaryConfig = TableConfig(
  WormbaseGeneSummary,
  ParseConfig(
    parse_gene_gff_summary,
    LocalDatastoreFileTemplate( 'GENE_GFF', MODULE_DB_OPERATIONS_BUCKET_NAME, RELEASE_FILEPATH, GENE_GFF_FILENAME ),
  ),
)

WormbaseGeneConfig = TableConfig(
  WormbaseGene,
  ParseConfig(
    parse_gene_gtf,
    LocalDatastoreFileTemplate( 'GENE_GFF', MODULE_DB_OPERATIONS_BUCKET_NAME, RELEASE_FILEPATH, GENE_GTF_FILENAME ),
    LocalDatastoreFileTemplate( 'GENE_GFF', MODULE_DB_OPERATIONS_BUCKET_NAME, RELEASE_FILEPATH, GENE_IDS_FILENAME ),
  ),
)

StrainAnnotatedVariantConfig = TableConfig(
  StrainAnnotatedVariant,
  ParseConfig(
    parse_strain_variant_annotation_data,
    LocalDatastoreFileTemplate( 'SVA_CSVGZ', MODULE_DB_OPERATIONS_BUCKET_NAME, SVA_FILEPATH, SVA_FILENAME ),
  ),
)

PhenotypeDatabaseConfig = TableConfig(
  PhenotypeDatabase,

  # Bulk file(s)
  ParseConfig(
    parse_phenotypedb_bulk_trait_file,
    *LocalDatastoreFileTemplate.from_file_record_entities(TraitFile, filter = lambda tf: tf.is_bulk_file),
  ),

  # Non-bulk files
  ParseConfig(
    parse_phenotypedb_traits_data,
    *LocalDatastoreFileTemplate.from_file_record_entities(TraitFile, filter = lambda tf: not tf.is_bulk_file),
  ),
)
