import os
import shutil
from logzero import logger

# Local imports
from .table_config import StrainConfig, WormbaseGeneSummaryConfig, WormbaseGeneConfig, StrainAnnotatedVariantConfig, PhenotypeDatabaseConfig

from caendr.models.datastore import Species
from caendr.utils.constants  import DEFAULT_BATCH_SIZE
from caendr.utils.data       import batch_generator



# Gather table configurations into a single dict
TABLE_CONFIG = {
    config.table_name: config for config in [
        StrainConfig,
        WormbaseGeneSummaryConfig,
        WormbaseGeneConfig,
        StrainAnnotatedVariantConfig,
        PhenotypeDatabaseConfig,
    ]
}



class DatabaseManager:

    # The default local directory to store all downloaded files in
    __DEFAULT_LOCAL_DIR = os.path.join('.', '.download')


    def __init__(self, app, db, reload_files: bool = False, local_directory: str = None):
        self.app = app
        self.db  = db

        # Set the local directory
        self._local_directory = local_directory or self.__DEFAULT_LOCAL_DIR

        # Prep the local directory
        if reload_files:
            self.reset_directory()
        self.ensure_directory_exists()


    #
    # Local Directory
    #

    def ensure_directory_exists(self):
        '''
            Ensures the local download directory exists, along with any relevant subdirectories.
        '''
        # Create a folder at the desired path if one does not yet exist
        os.makedirs(self._local_directory, exist_ok=True)

        # Make sure a subfolder exists for each species in the list
        for species_name in Species.all():
            os.makedirs( os.path.join(self._local_directory, species_name), exist_ok=True)


    def reset_directory(self):
        '''
            Deletes the local download directory and all its contents.
        '''
        logger.info('Creating empty directory to store downloaded files')
        if os.path.exists(self._local_directory):
            shutil.rmtree(self._local_directory)


    #
    # Tables
    #

    def all_tables(self):
        return list(self.db.metadata.tables.values())

    @staticmethod
    def print_tables(*tables):
        if not len(tables):
            return 'all tables'
        return 'tables: ' + ', '.join([ t.__tablename__ for t in tables ])



    #
    # Loading Tables
    #

    def load_tables(self, *tables, species_list = None):
        '''
            Load & insert data for one or more SQL tables.
            If no tables are passed, will load data for ALL tables.
        '''
        if len(tables) == 0:
            tables = self.all_tables()

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

            # Load & insert table data in batches, to help reduce local memory footprint
            logger.info(f'Inserting data for {species.name} into table {config.table_name}...')
            for i, g in enumerate(batch_generator( config.parse_for_species(species) )):
                logger.debug(f'Processing {species.name} batch {i} (rows {i * DEFAULT_BATCH_SIZE}-{(i+1) * DEFAULT_BATCH_SIZE})...')
                self.db.session.bulk_insert_mappings(config.table, g)
                self.db.session.commit()
                logger.debug(f'Finished inserting {species.name} batch {i}.')

        # Print how many entries were added
        total_records = config.table.query.count() - initial_count
        logger.info(f'Inserted {total_records} entries into table {config.table_name}')



    #
    # Clearing Tables
    #


    def __drop_all(self, *tables):
        '''
            Drop the given tables. If no tables are provided, drops all tables.
        '''
        if len(tables) == 0:
            self.db.drop_all(app=self.app)
        else:
            self.db.metadata.drop_all(bind=self.db.engine, checkfirst=True, tables=[ t.__table__ for t in tables ])

    def __create_all(self, *tables):
        '''
            Create the given tables. If no tables are provided, creates all tables.
        '''
        if len(tables) == 0:
            self.db.create_all(app=self.app)
        else:
            self.db.metadata.create_all(bind=self.db.engine, tables=[ t.__table__ for t in tables ])

    def __drop_species_rows(self, table, species):
        '''
            Drops all rows for the given species from the given table.
        '''
        del_statement = table.__table__.delete().where(table.__table__.c.species_name == species)
        self.db.engine.execute(del_statement)


    def clear_tables(self, *tables, species_list = None):
        '''
            Clear rows from one or more tables in the SQL db.

            Expects tables to be provided in dependency order:
            E.g., if table B contains a foreign key into table A, they should be provided as [... A, ..., B, ...]

            Args:
                *tables: List of tables to be cleared. If none are provided, clears all tables.
                species_list: List of species to clear the rows of. If `None`, clears *all* rows from the given tables.
        '''

        # If dropping all species, can perform bulk drop/create operations
        if species_list is None:
            logger.info(f'Dropping { self.print_tables(*tables) }...')
            self.__drop_all(*tables)
            logger.info(f'Creating { self.print_tables(*tables) }...')
            self.__create_all(*tables)

        # Otherwise, delete individual rows from tables
        else:
            logger.info(f'Dropping species [{", ".join(species_list)}] from { self.print_tables(*tables) }...')
            if tables is None:
                tables = self.all_tables()

            # Make sure all tables exist
            self.__create_all(*tables)

            # Loop through tables in reverse order, so rows that depend on earlier tables are dropped first
            for table in tables[::-1]:
                logger.info(f'Initial size of table { table.__tablename__ }: { table.query.count() }')

                for species_name in species_list:
                    self.__drop_species_rows(table, species_name)

                # Log size of table after drop
                logger.info(f'Size of table { table.__tablename__ } after dropping [{", ".join(species_list)}]: { table.query.count() }')

        # Commit changes
        self.db.session.commit()


    def clear_table(self, table, species_list = None):
        '''
            Clear rows from a table in the SQL db.

            Args:
                *tables: The table to be cleared.
                species_list: List of species to clear the rows of. If `None`, clears *all* rows from the given table.
        '''
        return self.clear_tables([table], species_list=species_list)
