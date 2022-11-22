import os

from caendr.utils.data import remove_env_escape_chars


# Get environment variables
MODULE_DB_OPERATIONS_BUCKET_NAME = os.environ.get('MODULE_DB_OPERATIONS_BUCKET_NAME')
STRAIN_VARIANT_ANNOTATION_PATH   = os.environ.get('STRAIN_VARIANT_ANNOTATION_PATH')


# Construct URL templates for external DBs (not managed by CaeNDR)
external_db_url_templates = {

    # URLs that depend on the species
    'specific': {
        'GENE_GTF_URL': remove_env_escape_chars(os.environ.get('GENE_GTF_URL')),
        'GENE_GFF_URL': remove_env_escape_chars(os.environ.get('GENE_GFF_URL')),
        'GENE_IDS_URL': remove_env_escape_chars(os.environ.get('GENE_IDS_URL')),
        'ORTHOLOG_URL': remove_env_escape_chars(os.environ.get('ORTHOLOG_URL')),
    },

    # URLs that don't depend on the species
    'generic': {
        'HOMOLOGENE_URL': remove_env_escape_chars(os.environ.get('HOMOLOGENE_URL')),
        'TAXON_ID_URL':   remove_env_escape_chars(os.environ.get('TAXON_ID_URL'))
    },
}


# Construct URL templates for internal DBs (managed by CaeNDR)
internal_db_blob_templates = {
  'SVA_CSVGZ_URL': f'{STRAIN_VARIANT_ANNOTATION_PATH}/WI.strain-annotation.bcsq.$SVA.csv.gz'
}


DEFAULT_LOCAL_DOWNLOAD_PATH = '.download'

# Expose the Taxon ID URL for external use (in the ETL module)
TAXON_ID_URL = external_db_url_templates['generic']['TAXON_ID_URL']
