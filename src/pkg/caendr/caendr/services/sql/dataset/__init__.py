import os
import re
import shutil

from logzero import logger

from caendr.models.error import BadRequestError, InternalError

# Import the taxonomic ID URL to expose it to external modules
from ._env import DEFAULT_LOCAL_DOWNLOAD_PATH, TAXON_ID_URL



class DatasetManager:

    def __init__(self,
        species_list,
        local_download_path: str = DEFAULT_LOCAL_DOWNLOAD_PATH,
        reload_files: bool = False,
    ):
        '''
          Args:
            species_list (dict(str), optional): [Dictionary mapping species IDs to species-specific values. Default provided.]
            local_download_path (str, optional): [Local directory path to store downloaded files. Defaults to '.download'.]
            reload_files (bool, optional): [Whether to clear the current contents of the download directory and re-download all files. Defaults to False.]
        '''

        # Set object variables
        self.local_download_path = local_download_path
        self.species_list = species_list

        # Locate directory
        if reload_files:
            self.reset_directory()
        self.ensure_directory_exists()


    ## Specific & Generic URL Template Names ##

    @property
    def specific_template_names(self):
        from ._env import external_db_url_templates
        return external_db_url_templates['specific'].keys()

    @property
    def generic_template_names(self):
        from ._env import external_db_url_templates
        return external_db_url_templates['generic'].keys()


    ## Species ##

    def get_species(self, species_name: str):
        '''
            Get a Species object from its name attribute.
        '''
        species = self.species_list.get(species_name)
        if species:
            return species
        else:
            logger.warning(f'Invalid Species Name: "{species_name}"')
            raise InternalError()


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

    from ._templates import (
        get_url,
        get_blob,
        get_filename,
        get_download_path,
    )

    from ._db_external import (
        prefetch_all_external_dbs,
        fetch_external_db,
        fetch_gene_gff_db,
        fetch_gene_gtf_db,
        fetch_gene_ids_db,
        fetch_homologene_db,
        fetch_ortholog_db,
        fetch_taxon_id_db,
    )

    from ._db_internal import (
        prefetch_all_internal_dbs,
        fetch_internal_db,
        fetch_sva_db,
    )
