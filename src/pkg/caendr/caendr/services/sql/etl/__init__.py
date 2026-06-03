import os
import shutil
import csv
import tempfile
from logzero import logger

# Local imports
from .table_config import StrainConfig, WormbaseGeneSummaryConfig, WormbaseGeneConfig, StrainAnnotatedVariantConfig, AnnovarAnnotatedVariantConfig, CsqAnnotatedVariantConfig, SnpEffAnnotatedVariantConfig, VepAnnotatedVariantConfig, PhenotypeDatabaseConfig, PhenotypeMetadataConfig

from caendr.models.datastore import Species
from caendr.models.sql       import ALL_SQL_TABLES
from caendr.utils.constants  import DEFAULT_BATCH_SIZE
from caendr.utils.data       import batch_generator
from caendr.services.cloud.postgresql import db

from sqlalchemy import func, literal_column, select

# Gather table configurations into a single dict
TABLE_CONFIG = {
    config.table_name: config for config in [
        StrainConfig,
        WormbaseGeneSummaryConfig,
        WormbaseGeneConfig,
        StrainAnnotatedVariantConfig,
        AnnovarAnnotatedVariantConfig,
        CsqAnnotatedVariantConfig,
        SnpEffAnnotatedVariantConfig,
        VepAnnotatedVariantConfig,
        PhenotypeDatabaseConfig,
        PhenotypeMetadataConfig
    ]
}


def query_count(query):
    return db.session.scalar(select(func.count()).select_from(query.subquery()))
    # ONE = literal_column("1")
    # counter = query.statement.with_only_columns(func.count(ONE))
    # counter = counter.order_by(None)
    # return db.session.execute(counter).scalar_one_or_none()


def table_row_count(table):
    return db.session.scalar(select(func.count()).select_from(table))


def generator_to_csv(data_generator, csv_file_path, fieldnames):
    '''
        Convert a generator of dictionaries to CSV file for COPY command.
        
        Args:
        data_generator: Generator yielding dictionaries
        csv_file_path: Path where CSV will be written
        fieldnames: List of column names
        
        Returns:
        Number of rows written
    '''
    rows_written = 0
    try:
        with open(csv_file_path, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
    
            for row in data_generator:
                writer.writerow(row)
                rows_written += 1
        
                if rows_written % 100000 == 0:
                    logger.debug(f'Exported {rows_written} rows to CSV')
    
        logger.info(f'Exported {rows_written} total rows to CSV: {csv_file_path}')
        return rows_written
    
    except Exception as e:
        logger.error(f'Failed to write CSV: {e}', exc_info=True)
        raise


class ETLManager:

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
        # return list(self.db.metadata.tables.values())
        return ALL_SQL_TABLES
    
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


    def load_table(self, table, species_list = None):
        '''
            Load & insert data for a single SQL table.
        '''

        # Get config object for the table
        config = TABLE_CONFIG[table.__tablename__]

        # Initialize a count for the number of entries added
        initial_count = query_count(table.query)
        logger.info(f'Initial count for table {config.table_name}: {initial_count} entries')

        # Determine if table can be loaded with COPY command (ie: it will replace the entire table))
        if species_list is None and config.replace_table:
            try:
                logger.info(f'Loading {config.table_name} with COPY command (full table replacement)...')
                data_generator = config.parse_for_all_species(species=None)  # Get a generator for all species at once, since we'll be replacing the whole table
                fieldnames = [ column.name for column in table.__table__.columns ]
                self.load_with_copy_from_generator(config.table_name, data_generator, fieldnames)
            except Exception as e:
                logger.error(f'COPY load failed for {config.table_name}, falling back to batch inserts: {e}', exc_info=True)
                self.resume_load_table(table, species_list)

        # If we can't use COPY (ie: we're only loading a subset of species, or the table is meant to be additive rather than replacing), use batch inserts
        data_generator = config.parse_for_all_species(species_list)
        total_inserted = self.bulk_insert_with_batching(
            table,
            data_generator, 
            batch_size=config.batch_size,
            defer_fks=True,
            disable_indexes=species_list is None and config.replace_table  # Disable indexes if we're replacing the whole table, since that will be faster than keeping them enabled during inserts and rebuilding after
        )
        logger.info(f"Inserted {total_inserted} {config.table_name} records with batch inserts for species [{', '.join(species_list) if species_list else 'all species'}]")


    def bulk_insert_with_batching(self, model_class, data_generator, batch_size=10000, 
                                  defer_fks=True, disable_indexes=False):
        '''
            Optimized bulk insert with batching, FK deferral, and optional index management.
            
            Args:
            model_class: SQLAlchemy model class to insert into
            data_generator: Generator or iterable yielding dictionaries to insert
            batch_size: Number of records to insert per batch (default 10000)
            defer_fks: Whether to defer FK constraints (default True)
            disable_indexes: Whether to disable indexes during insert (default False)
        '''
        if defer_fks:
            self.db.session.execute('SET CONSTRAINTS ALL DEFERRED')
        
        batch = []
        total_inserted = 0
        
        for data in data_generator:
            batch.append(data)
            
            if len(batch) >= batch_size:
                self.db.session.bulk_insert_mappings(model_class, batch)
                self.db.session.commit()
                total_inserted += len(batch)
                logger.info(f'Inserted {total_inserted} {model_class.__name__} records')
                batch = []
        
        if batch:
            self.db.session.bulk_insert_mappings(model_class, batch)
            self.db.session.commit()
            total_inserted += len(batch)
            logger.info(f'Inserted {total_inserted} {model_class.__name__} records (final batch)')
        
        return total_inserted


    def disable_indexes(self, table_name):
        '''Disable indexes on a table for faster bulk inserts.'''
        try:
            self.db.session.execute(f'ALTER TABLE {table_name} DISABLE TRIGGER ALL')
            self.db.session.commit()
            logger.info(f'Disabled indexes/triggers on {table_name}')
        except Exception as e:
            logger.warning(f'Could not disable indexes on {table_name}: {e}')


    def enable_indexes(self, table_name):
        '''Re-enable indexes on a table after bulk inserts.'''
        try:
            self.db.session.execute(f'ALTER TABLE {table_name} ENABLE TRIGGER ALL')
            self.db.session.commit()
            logger.info(f'Re-enabled indexes/triggers on {table_name}')
        except Exception as e:
            logger.warning(f'Could not re-enable indexes on {table_name}: {e}')


    def load_with_copy(self, table_name, csv_file_path, columns=None, disable_indexes_flag=True):
        '''
            Load data using PostgreSQL COPY command (native binary transfer, fastest method).
            
            Args:
            db: SQLAlchemy db instance
            table_name: Name of table to load into
            csv_file_path: Path to CSV file with data
            columns: List of column names to load (optional, uses all if None)
            disable_indexes_flag: Whether to disable indexes before load (default True)
            
            Returns:
            Number of rows loaded
        '''
        try:
            if disable_indexes_flag:
                self.disable_indexes(table_name)
        
            col_spec = f'({", ".join(columns)})' if columns else ''
        
            with open(csv_file_path, 'r') as f:
                copy_sql = f'COPY {table_name} {col_spec} FROM STDIN WITH (FORMAT csv, HEADER true, NULL \'\', ESCAPE E\'\\\')'
                conn = self.db.engine.raw_connection()
                cursor = conn.cursor()
                try:
                    cursor.copy_expert(copy_sql, f)
                    conn.commit()
                    rows_loaded = cursor.rowcount
                    logger.info(f'COPY loaded {rows_loaded} rows into {table_name}')
                finally:
                    cursor.close()
                    conn.close()
        
            if disable_indexes_flag:
                self.enable_indexes(table_name)
        
            return rows_loaded
        
        except Exception as e:
            logger.error(f'COPY command failed for {table_name}: {e}', exc_info=True)
            raise


    def load_with_copy_from_generator(self, table_name, data_generator, fieldnames, disable_indexes_flag=True):
        '''
            Complete pipeline: generator -> CSV -> COPY command.
            Combines streaming data processing with native COPY for maximum performance.
            
            Args:
            db: SQLAlchemy db instance
            table_name: Name of table to load into
            data_generator: Generator yielding dictionaries
            fieldnames: List of column names
            disable_indexes_flag: Whether to disable indexes before load (default True)
            
            Returns:
            Number of rows loaded
        '''
        csv_file_path = None
        try:
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
            csv_file_path = temp_file.name
            temp_file.close()
            
            logger.info(f'Exporting data to temporary CSV: {csv_file_path}')
            generator_to_csv(data_generator, csv_file_path, fieldnames)
            
            logger.info(f'Loading from CSV into {table_name} using COPY')
            rows_loaded = self.load_with_copy(table_name, csv_file_path, fieldnames, disable_indexes_flag)
            
            return rows_loaded
    
        finally:
            # Clean up temporary CSV file
            if csv_file_path and os.path.exists(csv_file_path):
                os.remove(csv_file_path)
                logger.debug(f'Cleaned up temporary CSV file')


    def rebuild_indexes(self, table_name):
        '''Rebuild/reindex a table after bulk operations for optimal query performance.'''
        try:
            logger.info(f'Starting index rebuild for {table_name}...')
            self.db.session.execute(f'REINDEX TABLE {table_name}')
            self.db.session.commit()
            logger.info(f'Index rebuild completed for {table_name}')
        except Exception as e:
            logger.warning(f'Could not rebuild indexes on {table_name}: {e}')


    def resume_load_table(self, table, species_list = None):
        '''
            Load & insert data for a single SQL table, resuming from the current size of the table.
        '''

        # Get config object for the table
        config = TABLE_CONFIG[table.__tablename__]

        # Initialize a count for the number of entries added
        initial_count = query_count(config.table.query)
        logger.info(f'Initial count for table {config.table_name}: {initial_count} entries')

        # Loop through the name & Species object for each species
        for species in Species.all().values():

            # Skip any species not in the list
            if species_list and species.name not in species_list:
                continue

            # Find number of entries in table for species
            current_count = query_count(config.table.query.filter(table.__table__.c.species_name == species.name))
            # current_count = select(func.count(table.__table__.c.id)).filter(table.__table__.c.species_name == species.name).scalar_one_or_none()
            logger.info(f"There are {current_count} entries in {config.table_name} for {species.name}")

            # Load & insert table data in batches, to help reduce local memory footprint
            logger.info(f'Inserting data for {species.name} into table {config.table_name}...')
            for i, g in enumerate(batch_generator( config.parse_for_species(species) )):
                if i * DEFAULT_BATCH_SIZE < current_count:
                    logger.debug(f'Skipping {species.name} batch {i} (rows {i * DEFAULT_BATCH_SIZE}-{(i+1) * DEFAULT_BATCH_SIZE})...')
                    for j in g:
                        continue
                    continue
                logger.debug(f'Processing {species.name} batch {i} (rows {i * DEFAULT_BATCH_SIZE}-{(i+1) * DEFAULT_BATCH_SIZE})...')
                self.db.session.bulk_insert_mappings(config.table, g)
                self.db.session.commit()
                logger.debug(f'Finished inserting {species.name} batch {i}.')

        # Print how many entries were added
        total_records = query_count(config.table.query) - initial_count
        logger.info(f'Inserted {total_records} entries into table {config.table_name}')


    #
    # Clearing Tables
    #

    def __drop_all(self, *tables):
        '''
            drop_tables [Drops tables from the SQL db. Drops all tables if non are provided. ]
            Args:
                tables (optional): List of tables to be dropped. Defaults to [] (ie: all tables)
        '''  
        if len(tables) == 0:
            logger.info('Dropping all tables...')
            self.db.drop_all(app=self.app)
        else:
            logger.info(f'Dropping tables: ${tables}')
            self.db.metadata.drop_all(bind=self.db.engine, checkfirst=True, tables=[ t.__table__ for t in tables ])
        self.db.session.commit()


    def __create_all(self, *tables):
        '''
            Create the given tables. If no tables are provided, creates all tables.
        '''
        if len(tables) == 0:
            logger.info('Creating all tables...')
            self.db.create_all(app=self.app)
        else:
            logger.info(f'Creating tables: ${tables}')
            self.db.metadata.create_all(bind=self.db.engine, tables=[ t.__table__ for t in tables ])


    def __drop_species_rows(self, table, species):
        '''
            Drops all rows for the given species from the given table.
        '''
        del_statement = table.__table__.delete().where(table.__table__.c.species_name == species)
        self.db.session.execute(del_statement)


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
                logger.info(f'Initial size of table { table.__tablename__ }: { table_row_count(table) }')

                for species_name in species_list:
                    self.__drop_species_rows(table, species_name)

                # Log size of table after drop
                logger.info(f'Size of table { table.__tablename__ } after dropping [{", ".join(species_list)}]: { table_row_count(table) }')

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

    def drop_tables(self, *tables, species_list = None):
        '''
            Drops rows from one or more tables in the SQL db.

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

        # Otherwise, delete individual rows from tables
        else:
            logger.info(f'Dropping species [{", ".join(species_list)}] from { self.print_tables(*tables) }...')
            if tables is None:
                tables = self.all_tables()

            # Make sure all tables exist
            self.__create_all(*tables)

            # Loop through tables in reverse order, so rows that depend on earlier tables are dropped first
            for table in tables[::-1]:
                logger.info(f'Initial size of table { table.__tablename__ }: { table_row_count(table) }')

                for species_name in species_list:
                    self.__drop_species_rows(table, species_name)

                # Log size of table after drop
                logger.info(f'Size of table { table.__tablename__ } after dropping [{", ".join(species_list)}]: { table_row_count(table) }')

        # Commit changes
        self.db.session.commit()


    def drop_table(self, table, species_list = None):
        '''
            Clear rows from a table in the SQL db.

            Args:
                *tables: The table to be cleared.
                species_list: List of species to clear the rows of. If `None`, clears *all* rows from the given table.
        '''
        return self.drop_tables([table], species_list=species_list)
