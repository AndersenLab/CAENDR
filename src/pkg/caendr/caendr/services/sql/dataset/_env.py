import os

from caendr.utils.env import get_env_var, remove_env_escape_chars


# Get environment variables
MODULE_DB_OPERATIONS_BUCKET_NAME = get_env_var('MODULE_DB_OPERATIONS_BUCKET_NAME')
STRAIN_VARIANT_ANNOTATION_PATH   = get_env_var('STRAIN_VARIANT_ANNOTATION_PATH')
DB_OPS_FILEPATH                  = get_env_var('DB_OPS_FILEPATH')


# Construct URL templates for external DBs (not managed by CaeNDR)
# TODO: Is this even still necessary?
external_db_url_templates = {

    # URLs that depend on the species
    'specific': {},

    # URLs that don't depend on the species
    'generic': {},
}


# Construct URL templates for internal DBs (managed by CaeNDR)
internal_db_blob_templates = {
    'GENE_GTF': remove_env_escape_chars( DB_OPS_FILEPATH + get_env_var('GENE_GTF_FILENAME') ),
    'GENE_GFF': remove_env_escape_chars( DB_OPS_FILEPATH + get_env_var('GENE_GFF_FILENAME') ),
    'GENE_IDS': remove_env_escape_chars( DB_OPS_FILEPATH + get_env_var('GENE_IDS_FILENAME') ),
    'SVA_CSVGZ': f'{STRAIN_VARIANT_ANNOTATION_PATH}/WI.strain-annotation.bcsq.$SVA.csv.gz',
}


DEFAULT_LOCAL_DOWNLOAD_PATH = '.download'

# Expose the taxonomic ID URL for external use (in the ETL module)
TAXON_ID_URL = external_db_url_templates['generic'].get('TAXON_ID')
