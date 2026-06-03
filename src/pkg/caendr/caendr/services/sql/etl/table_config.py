from typing import Dict, List

from caendr.utils.env              import get_env_var, get_env_var_with_fallback
from caendr.services.cloud.secret  import get_secret
from caendr.services.logger        import logger

# Local imports
from .strains                      import fetch_andersen_strains
from .wormbase                     import parse_gene_gtf, parse_gene_gff_summary
from .strain_annotated_variants    import parse_strain_variant_annotation_data, parse_annovar_variant_annotation_data, parse_csq_variant_annotation_data, parse_snpeff_variant_annotation_data, parse_vep_variant_annotation_data
from .phenotype_db                 import parse_phenotypedb_traits_data, parse_phenotypedb_bulk_trait_file
from .phenotype_metadata           import parse_phenotype_metadata

from caendr.models.sql             import Strain, WormbaseGeneSummary, WormbaseGene, StrainAnnotatedVariant, AnnovarAnnotatedVariant, CsqAnnotatedVariant, SnpEffAnnotatedVariant, VepAnnotatedVariant, PhenotypeDatabase, PhenotypeMetadata
from caendr.models.datastore       import Species, TraitFile
from caendr.services.cloud.storage import BlobURISchema
from caendr.models.datastore       import Species
from caendr.utils.local_files      import ForeignResource, ForeignResourceTemplate, LocalDatastoreFileTemplate, LocalGoogleSheetTemplate
from caendr.models.error           import ForeignResourceMissingError



# Bucket(s)
MODULE_DB_OPERATIONS_BUCKET_NAME = get_env_var('MODULE_DB_OPERATIONS_BUCKET_NAME')
AWS_BUCKET_NAME = get_env_var('AWS_OPEN_DATA_BUCKET')

# Filepaths
RELEASE_FILEPATH   = get_env_var('MODULE_DB_OPERATIONS_RELEASE_FILEPATH',   as_template=True)
SVA_FILEPATH       = get_env_var('MODULE_DB_OPERATIONS_SVA_FILEPATH',       as_template=True)
NEWSVA_FILEPATH    = get_env_var('MODULE_DB_OPERATIONS_NEWSVA_FILEPATH',    as_template=True)
PHENOTYPE_FILEPATH = get_env_var('MODULE_DB_OPERATIONS_PHENOTYPE_FILEPATH', as_template=True)

# Filenames
GENE_GFF_FILENAME    = get_env_var('GENE_GFF_FILENAME',  as_template=True)
GENE_GTF_FILENAME    = get_env_var('GENE_GTF_FILENAME',  as_template=True)
GENE_IDS_FILENAME    = get_env_var('GENE_IDS_FILENAME',  as_template=True)
SVA_FILENAME         = get_env_var('SVA_CSVGZ_FILENAME', as_template=True)
SVA_ANNOVAR_FILENAME = get_env_var('SVA_ANNOVAR_FILENAME', as_template=True)
SVA_CSQ_FILENAME     = get_env_var('SVA_CSQ_FILENAME', as_template=True)
SVA_SNPEFF_FILENAME  = get_env_var('SVA_SNPEFF_FILENAME', as_template=True)
SVA_VEP_FILENAME     = get_env_var('SVA_VEP_FILENAME', as_template=True)


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

  def __init__(self, parse, *files: ForeignResourceTemplate,):
    self.parse = parse
    self.files = files


  def fetch_all(self, species) -> Dict[str, ForeignResource]:
    '''
      Fetch all the files required for this species.
    '''
    result = {}
    for file_template in self.files:
      try:
        if file_template.has_for_species(species):
          result[file_template.resource_id] = file_template.get_for_species(species).fetch()
      except ForeignResourceMissingError as ex:
        logger.error(f'Skipping {file_template.get_print_uri(species)}: {ex}')
    logger.debug(f'Fetched {len(result)} files out of {len(self.files)} requested.')
    return result


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

  def __init__(self, table, *parse_configs: ParseConfig, replace_table=True, batch_size=10000):
    self.table = table
    self._parse_configs = parse_configs
    self.replace_table = replace_table
    self.batch_size = batch_size

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


  def parse_for_all_species(self, species_list=None):
    '''
      Apply all parsing functions in this config to their associated files for each species in the list,
      yielding from each set in sequence.
    '''
    if species_list is None:
      species_list = Species.query_ds()
    for species in species_list:
      yield from self.parse_for_species(species)


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
    LocalDatastoreFileTemplate( 'GENE_GTF', MODULE_DB_OPERATIONS_BUCKET_NAME, RELEASE_FILEPATH, GENE_GTF_FILENAME ),
    LocalDatastoreFileTemplate( 'GENE_IDS', MODULE_DB_OPERATIONS_BUCKET_NAME, RELEASE_FILEPATH, GENE_IDS_FILENAME ),
  ),
)

StrainAnnotatedVariantConfig = TableConfig(
  StrainAnnotatedVariant,
  ParseConfig(
    parse_strain_variant_annotation_data,
    LocalDatastoreFileTemplate( 'SVA_CSVGZ', MODULE_DB_OPERATIONS_BUCKET_NAME, SVA_FILEPATH, SVA_FILENAME ),
  ),
  batch_size=50000,
)

AnnovarAnnotatedVariantConfig = TableConfig(
  AnnovarAnnotatedVariant,
  ParseConfig(
    parse_annovar_variant_annotation_data,
    LocalDatastoreFileTemplate( 'ANNOVAR', AWS_BUCKET_NAME, NEWSVA_FILEPATH, SVA_ANNOVAR_FILENAME, gcp=False ),
  ),
  batch_size=50000,
)

CsqAnnotatedVariantConfig = TableConfig(
  CsqAnnotatedVariant,
  ParseConfig(
    parse_csq_variant_annotation_data,
    LocalDatastoreFileTemplate( 'CSQ', AWS_BUCKET_NAME, NEWSVA_FILEPATH, SVA_CSQ_FILENAME, gcp=False ),
  ),
  batch_size=50000,
)

SnpEffAnnotatedVariantConfig = TableConfig(
  SnpEffAnnotatedVariant,
  ParseConfig(
    parse_snpeff_variant_annotation_data,
    LocalDatastoreFileTemplate( 'SNPEFF', AWS_BUCKET_NAME, NEWSVA_FILEPATH, SVA_SNPEFF_FILENAME, gcp=False ),
  ),
  batch_size=50000,
)

VepAnnotatedVariantConfig = TableConfig(
  VepAnnotatedVariant,
  ParseConfig(
    parse_vep_variant_annotation_data,
    LocalDatastoreFileTemplate( 'VEP', AWS_BUCKET_NAME, NEWSVA_FILEPATH, SVA_VEP_FILENAME, gcp=False ),
  ),
  batch_size=50000,
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
  replace_table=False,  # Don't replace the table when loading non-bulk files, since they are meant to be additive to the bulk file data already in the table 
)

PhenotypeMetadataConfig = TableConfig(
  PhenotypeMetadata,
  ParseConfig(
    parse_phenotype_metadata,
    *LocalDatastoreFileTemplate.from_file_record_entities(TraitFile),
  )
)
