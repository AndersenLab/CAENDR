import os

from caendr.utils.env import get_env_var, remove_env_escape_chars


# Get environment variables
MODULE_DB_OPERATIONS_BUCKET_NAME = get_env_var('MODULE_DB_OPERATIONS_BUCKET_NAME')
RELEASE_FILEPATH = get_env_var('MODULE_DB_OPERATIONS_RELEASE_FILEPATH', as_template=True)
SVA_FILEPATH     = get_env_var('MODULE_DB_OPERATIONS_SVA_FILEPATH',     as_template=True)


# Construct URL templates for external DBs (not managed by CaeNDR)
# TODO: Is this even still necessary?
external_db_url_templates = {

    # URLs that depend on the species
    'specific': {},

    # URLs that don't depend on the species
    'generic': {},
}


# Construct URL templates for internal DBs (managed by CaeNDR)
# TODO: Keep these variables as TokenizedStrings
internal_db_blob_templates = {
    'GENE_GTF':  f'{RELEASE_FILEPATH.raw_string}/{get_env_var("GENE_GTF_FILENAME")}',
    'GENE_GFF':  f'{RELEASE_FILEPATH.raw_string}/{get_env_var("GENE_GFF_FILENAME")}',
    'GENE_IDS':  f'{RELEASE_FILEPATH.raw_string}/{get_env_var("GENE_IDS_FILENAME")}',
    'SVA_CSVGZ': f'{SVA_FILEPATH.raw_string}/{get_env_var("SVA_CSVGZ_FILENAME", as_template=True).raw_string}',
}


DEFAULT_LOCAL_DOWNLOAD_PATH = '.download'

# Expose the taxonomic ID URL for external use (in the ETL module)
TAXON_ID_URL = external_db_url_templates['generic'].get('TAXON_ID')
