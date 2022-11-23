import os
import shutil

from logzero import logger

from caendr.models.error import BadRequestError

# Import the taxonomic ID URL to expose it to external modules
from .env import DEFAULT_LOCAL_DOWNLOAD_PATH, TAXON_ID_URL


# List of species, with associated project number(s) and wormbase version
# TODO: This information should probably be read from somewhere else
species_list = {
    'c_elegans': {
        'project_number':   'PRJNA13758',
        'wormbase_version': os.environ.get('WORMBASE_VERSION'),
    },
#   'c_briggsae': {
#     'project_number':   'PRJNA10731',
#     'wormbase_version': 'WS285',
#   },
}


class DatasetManager:

    def __init__(self,
        wb_ver:  str = None,
        sva_ver: str = None,
        local_download_path: str = DEFAULT_LOCAL_DOWNLOAD_PATH,
        species_list = species_list,
        reload_files: bool = False,
    ):
        '''
        Args:
            wb_ver (str, optional): [Version of Wormbase Data to use (ie: WS276). Optional for initialization, but required for some operations.]
            sva_ver (str, optional): [Strain Variant Annotation version to use. Optional for initialization, but required for some operations.]
            local_download_path (str, optional): [Local directory path to store downloaded files. Defaults to '.download'.]
            species_list (dict(str), optional): [Dictionary mapping species IDs to species-specific values. Default provided.]
            reload_files (bool, optional): [Whether to clear the current contents of the download directory and re-download all files. Defaults to False.]
        '''

        # Set version properties
        self.wb_ver  = wb_ver
        self.sva_ver = sva_ver

        self.local_download_path = local_download_path
        self.species_list = species_list

        # Locate directory
        if reload_files:
            self.reset_directory()
        self.ensure_directory_exists()


    ## Property: wb_ver (WormBase Version) ##

    @property
    def wb_ver(self):

        # Throw an error if trying to get the version before it's been set
        if not self._wb_ver:
            logger.warning("E_NOT_SET: 'wb_ver' (WormBase Version)")
            raise BadRequestError()

        # Otherwise, return the version
        return self._wb_ver

    @wb_ver.setter
    def wb_ver(self, new_wb_ver: str):
        # TODO: validate
        # wb_regex = r'^WS[0-9]*$'      # Match the expected format: 'WS276'
        self._wb_ver = new_wb_ver


    ## Property: sva_ver (Strain Variant Annotation Version) ##

    @property
    def sva_ver(self):
        if not self._sva_ver:
            logger.warning("E_NOT_SET: 'sva_ver' (Strain Variant Annotation Version)")
            raise BadRequestError()
        return self._sva_ver

    @sva_ver.setter
    def sva_ver(self, new_sva_ver: str):
        # TODO: validate
        self._sva_ver = new_sva_ver


    ## Specific & Generic URL Template Names ##

    @property
    def specific_template_names(self):
        from .env import external_db_url_templates
        return external_db_url_templates['specific'].keys()

    @property
    def generic_template_names(self):
        from .env import external_db_url_templates
        return external_db_url_templates['generic'].keys()


    ## Directory ##

    def ensure_directory_exists(self):
        '''
            Ensures the local download directory exists and has the correct subfolders.
        '''
        # Create a folder at the desired path if one does not yet exist
        if not os.path.exists(self.local_download_path):
            os.mkdir(self.local_download_path)

        # Make sure a subfolder exists for each species in the list
        for species_name in self.species_list.keys():
            species_path = f'{self.local_download_path}/{species_name}'
            if not os.path.exists(species_path):
                os.mkdir(species_path)


    def reset_directory(self):
        '''
            Deletes the local download directory and all its contents.
        '''
        logger.info('Creating empty directory to store downloaded files')
        if os.path.exists(self.local_download_path):
            shutil.rmtree(self.local_download_path)


    ## Import functions from this module as class methods ##

    from .url_templates import get_url, get_filename

    from .db_external import (
        prefetch_all_external_dbs,
        fetch_external_db,
        fetch_gene_gff_db,
        fetch_gene_gtf_db,
        fetch_gene_ids_db,
        fetch_homologene_db,
        fetch_ortholog_db,
        fetch_taxon_id_db,
    )

    from .db_internal import (
        prefetch_all_internal_dbs,
        fetch_internal_db,
        fetch_sva_db,
    )
