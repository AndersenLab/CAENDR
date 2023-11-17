from logzero import logger

# Local imports
from .table_config import StrainConfig, WormbaseGeneSummaryConfig, WormbaseGeneConfig, StrainAnnotatedVariantConfig

from caendr.models.datastore     import Species
from caendr.services.sql.dataset import DatasetManager
from caendr.utils.data           import batch_generator



# Gather table configurations into a single dict
TABLE_CONFIG = {
    config.table_name: config for config in [
        StrainConfig,
        WormbaseGeneSummaryConfig,
        WormbaseGeneConfig,
        StrainAnnotatedVariantConfig,
    ]
}



class ETLManager:

    def __init__(self, db, species_list, reload_files: bool = False):
        self.db = db
        self.dataset_manager = DatasetManager(species_list=species_list, reload_files=reload_files)

    def prefetch_all_dbs(self, use_cache: bool = True):
        self.dataset_manager.prefetch_all_external_dbs(use_cache=use_cache)
        self.dataset_manager.prefetch_all_internal_dbs(use_cache=use_cache)


    ## Species ##

    @property
    def species_list(self):
        return self.dataset_manager.species_list

    def get_species(self, species_name: str):
        return self.dataset_manager.get_species(species_name)


    ## Download Path ##

    @property
    def local_download_path(self):
        return self.dataset_manager.local_download_path

    def get_download_path(self, species_name):
        return f"{self.local_download_path}/{species_name}"



    ## Loading Tables ##

    def load_tables(self, *tables, species_list = None):
        '''
            Load & insert data for one or more SQL tables.
            If no tables are passed, will load data for ALL tables.
        '''
        for table in tables:
            self.load_table(table, species_list=species_list)


    # Is this link still relevant?
    # https://github.com/phil-bergmann/2016_DLRW_brain/blob/3f69c945a40925101c58a3d77c5621286ad8d787/brain/data.py

    def load_table(self, table, species_list = None):
        '''
            Load & insert data for a single SQL table.
        '''

        # Get config object for the table
        config = TABLE_CONFIG[table.__tablename__]

        # Initialize a count for the number of entries added
        initial_count = config.table.query.count()
        logger.info(f'Initial count for table {config.table_name}: {initial_count} entries')

        # Loop through the name & Species object for each species
        for species in Species.all().values():

            # Skip any species not in the list
            if species_list and species.name not in species_list:
                continue

            logger.info(f'Inserting data for {species.name} into table {config.table_name}...')
            for g in batch_generator( config.parse_for_species(species) ):
                self.db.session.bulk_insert_mappings(config.table, g)
                self.db.session.commit()

        # Print how many entries were added
        total_records = config.table.query.count() - initial_count
        logger.info(f'Inserted {total_records} entries into table {config.table_name}')
