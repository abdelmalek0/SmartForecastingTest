from datetime import datetime, date, timedelta
from psycopg2 import sql, pool, OperationalError, InterfaceError
import psycopg2
import pandas as pd
from structs.models import DataPoint
from utility import read_config
from logging_config import logger


class DatabaseHandler:

    def __init__(self, config):
        self.config = config
        self.conn_pool = None
        self.connection = None
        self.cursor = None
        self.last_used = datetime.now()

    def create_pool(self):
        """Create a connection pool for efficient connection management."""
        try:
            self.conn_pool = psycopg2.pool.SimpleConnectionPool(
                minconn=1,
                maxconn=20,
                host=self.config['database']['host'],
                port=self.config['database']['port'],
                dbname=self.config['database']['dbname'],
                user=self.config['database']['user'],
                password=self.config['database']['password'],
                sslmode=self.config['database']['sslmode']
            )
            logger.info("Database connection pool created successfully.")
        except Exception as e:
            logger.error(f"Failed to create connection pool: {e}")
            raise e

    def connect(self):
        """Connect to the database using a pooled connection."""
        try:
            if not self.conn_pool:
                self.create_pool()

            self.connection = self.conn_pool.getconn()
            self.cursor = self.connection.cursor()
            self.last_used = datetime.now()
            logger.info("Connected to database using connection pool.")
        except OperationalError as e:
            logger.error(f"Operational error during connection: {e}")
            raise e
        except Exception as e:
            logger.error(f"Error connecting to the database: {e}")
            raise e

    def disconnect(self):
        """Disconnect from the database and return the connection to the pool."""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            if self.conn_pool:
                self.conn_pool.putconn(self.connection)
            else:
                self.connection.close()
        logger.info("Disconnected from database and connection returned to pool.")

    def check_and_reconnect(self):
        """Check the connection status and attempt to reconnect if needed."""
        try:
            if not self.connection or self.connection.closed != 0:
                logger.info("Connection is closed or not established. Reconnecting...")
                self.connect()
            else:
                # Check if the connection is still alive
                self.connection.poll()
                self.last_used = datetime.now()
        except (OperationalError, InterfaceError) as e:
            logger.warning(f"Connection error detected: {e}. Attempting reconnection...")
            self.connect()

    def execute_statement(self, statement, params=None):
        """Execute a SQL statement with automatic reconnection handling."""
        self.check_and_reconnect()
        try:
            if params:
                self.cursor.execute(statement, params)
            else:
                self.cursor.execute(statement)
            self.connection.commit()
            self.last_used = datetime.now()
        except (OperationalError, InterfaceError) as e:
            logger.warning(f"Connection error: {e}. Retrying after reconnect...")
            self.connect()
            if params:
                self.cursor.execute(statement, params)
            else:
                self.cursor.execute(statement)
            self.connection.commit()
            self.last_used = datetime.now()
        except Exception as e:
            logger.error(f"Error executing statement: {e}")
            self.connection.rollback()
            raise e

    def insert_dataframe(self, df: pd.DataFrame, ds_id: int):
        logger.info(f'Inserting data for data source ID: {ds_id}')

        table_name = self.config['database']['data-sources-table-name']
        for index, row in df.iterrows():
            # Create INSERT statement
            insert_statement = sql.SQL("INSERT INTO {} (datasource_id, ts, value) VALUES ({})").format(
                sql.Identifier(table_name),
                sql.SQL(', ').join(map(sql.Literal, [ds_id] + row.to_list()))
            )
            # Execute INSERT statement
            self.execute_statement(insert_statement)

    def add_data_point(self, data_point: DataPoint, ds_id: int):
        logger.info(f"Inserting data for data source ID: {ds_id}")

        table_name = self.config['database']['data-sources-table-name']

        # First, check if a datapoint with the same ds_id and ts already exists
        check_statement = sql.SQL("SELECT COUNT(*) FROM {} WHERE datasource_id = %s AND ts = %s").format(
            sql.Identifier(table_name)
        )
        self.execute_statement(check_statement, (ds_id, data_point.ts))
        count = self.cursor.fetchone()[0]

        if count > 0:
            logger.info(f"Datapoint for data source ID: {ds_id} at timestamp: {data_point.ts} already exists. Skipping insertion.")
            return 0

        # If no existing datapoint found, proceed with insertion
        insert_statement = sql.SQL("INSERT INTO {} (datasource_id, ts, value) VALUES ({})").format(
            sql.Identifier(table_name),
            sql.SQL(', ').join(map(sql.Literal, [ds_id, data_point.ts, data_point.value]))
        )
        # Execute INSERT statement
        self.execute_statement(insert_statement)
        logger.info(f"Datapoint for data source ID: {ds_id} at timestamp: {data_point.ts} inserted successfully.")
        return 1

    def get_data_point(self, ds_id: int, ts: date | datetime) -> float:
        logger.info(f"Retrieving data point for data source ID: {ds_id} at timestamp: {ts}")

        table_name = self.config['database']['data-sources-table-name']

        select_statement = sql.SQL("SELECT * FROM {table} WHERE datasource_id = %s AND ts = %s").format(
            table=sql.Identifier(table_name)
        )

        # Print the query for debugging
        logger.info("Executing query: %s", select_statement.as_string(self.cursor))

        try:
            # Execute the query
            self.execute_statement(select_statement, (ds_id, ts))
            result = self.cursor.fetchone()

            # Print the result for debugging
            logger.info(f"Query result: {result}")

            if result:
                return result[2]
            else:
                return -1
        except Exception as e:
            logger.error(f"An error occurred while retrieving data: {e}")
            return -1

    def update_data_point(self, data_point: DataPoint, ds_id: int):
        logger.info(f"Updating data point for data source ID: {ds_id} at timestamp: {data_point.ts}")

        table_name = self.config['database']['data-sources-table-name']

        # Create UPDATE statement
        update_statement = sql.SQL("UPDATE {table} SET value = %s WHERE datasource_id = %s AND ts = %s").format(
            table=sql.Identifier(table_name)
        )

        # Print the query for debugging
        logger.info("Executing query:  %s", update_statement.as_string(self.cursor))

        try:
            # Execute UPDATE statement
            self.execute_statement(update_statement, (data_point.value, ds_id, data_point.ts))

            # Check if any row was updated
            if self.cursor.rowcount > 0:
                logger.info("Update successful.")
            else:
                logger.info("No rows were updated. Verify if the data point exists.")
        except Exception as e:
            logger.error(f"An error occurred while updating data: {e}")
            self.connection.rollback()
    
    def delete_data_point(self, ds_id: int, ts: date | datetime) -> int:
        """
        Delete a data point from the database by dropping the partition containing the given timestamp
        and reinserting all data except the one to be deleted.
        
        :param ds_id: The data source ID.
        :param ts: The timestamp of the data point to be deleted.
        """
        logger.info(f"Deleting data point for data source ID: {ds_id} at timestamp: {ts}")

        table_name = self.config['database']['data-sources-table-name']
        temp_table_name = f"{table_name}_temp"

        # Check if the data point exists before deletion
        exists_before = self.get_data_point(ds_id, ts)
        if exists_before == -1: return 0

        # Step 1: Create a temporary table with all data except the one to delete
        create_temp_table_statement = sql.SQL(
            """
            CREATE TABLE {temp_table} AS (
            SELECT * FROM {main_table}
            WHERE NOT (datasource_id = %s AND ts = %s))
            """
        ).format(
            temp_table=sql.Identifier(temp_table_name),
            main_table=sql.Identifier(table_name)
        )

        # Step 2: Drop the original table
        drop_original_table_statement = sql.SQL(
            "DROP TABLE {main_table}"
        ).format(
            main_table=sql.Identifier(table_name)
        )

        # Step 3: Rename the temporary table to the original table name
        rename_temp_to_original_statement = sql.SQL(
            "RENAME TABLE {temp_table} TO {main_table};"
        ).format(
            main_table=sql.Identifier(table_name),
            temp_table=sql.Identifier(temp_table_name)
        )

        try:
            # Execute all steps
            self.execute_statement(create_temp_table_statement, (ds_id, ts))
            self.execute_statement(drop_original_table_statement)
            self.execute_statement(rename_temp_to_original_statement)

            # Check if the data point still exists after deletion
            exists_after = self.get_data_point(ds_id, ts)

            if exists_after == -1:
                logger.info(f"Data point for data source ID: {ds_id} at timestamp: {ts} was successfully deleted.")
                return 1
            else:
                logger.warning(f"Data point for data source ID: {ds_id} at timestamp: {ts} may not have been deleted correctly.")
                return 0
        except Exception as e:
            logger.error(f"An error occurred while deleting data point: {e}")
            self.connection.rollback()
            return -1
       
    def delete_datasource(self, ds_id: int) -> int:
        """
        Delete data points from the database by dropping the partition containing
        the given data source ID and reinserting all data except the one to be deleted.

        :param ds_id: The data source ID to be deleted.
        :return: 1 if successful, -1 if an error occurs.
        """
        logger.info(f"Deleting data point for data source ID: {ds_id}")

        table_name = self.config['database']['data-sources-table-name']
        temp_table_name = f"{table_name}_temp"

        try:
            # Step 1: Create a temporary table with all data except the one to delete
            create_temp_table_sql = sql.SQL(
                """
                CREATE TABLE {temp_table} AS (
                SELECT * FROM {main_table}
                WHERE (datasource_id != %s) )
                """
            ).format(
                temp_table=sql.Identifier(temp_table_name),
                main_table=sql.Identifier(table_name)
            )
            self.execute_statement(create_temp_table_sql, (ds_id, ))

            # Step 2: Drop the original table
            drop_original_table_sql = sql.SQL(
                "DROP TABLE {main_table}"
            ).format(
                main_table=sql.Identifier(table_name)
            )
            self.execute_statement(drop_original_table_sql)

            # Step 3: Rename the temporary table to the original table name
            rename_temp_table_sql = sql.SQL(
                "RENAME TABLE {temp_table} TO {main_table}"
            ).format(
                temp_table=sql.Identifier(temp_table_name),
                main_table=sql.Identifier(table_name)
            )
            self.execute_statement(rename_temp_table_sql)

            return 1
        except Exception as e:
            logger.error(f"An error occurred while deleting data point: {e}")
            self.connection.rollback()
            return -1

    def get_all_data_for_datasource(self, ds_id: int) -> pd.DataFrame:
        logger.info(f"Retrieving all data for data source ID: {ds_id}")

        table_name = self.config['database']['data-sources-table-name']
        select_statement = sql.SQL("SELECT * FROM {table} WHERE datasource_id = %s ORDER BY ts").format(
            table=sql.Identifier(table_name)
        )
        logger.info("Executing query: %s", select_statement.as_string(self.cursor))

        try:
            self.execute_statement(select_statement, (ds_id,))
            result = self.cursor.fetchall()

            # Convert the result to a DataFrame
            df = pd.DataFrame(result, columns=['datasource_id', 'ts', 'value'])
            return df[['ts', 'value']]
        except Exception as e:
            logger.error(f"An error occurred while retrieving all data: {e}")
            return pd.DataFrame(columns=['ts', 'value'])

    def get_latest_data_points(self, datasource_id: int, lags: int) -> pd.DataFrame:
        logger.info(f"Retrieving latest {lags} data points for data source ID: {datasource_id}")

        table_name = self.config['database']['data-sources-table-name']
        select_statement = sql.SQL("""
            SELECT * FROM (
                SELECT * FROM {table} WHERE datasource_id = %s ORDER BY ts DESC LIMIT %s
            ) AS latest_data ORDER BY ts ASC
        """).format(
            table=sql.Identifier(table_name)
        )

        # Print the query for debugging
        logger.info("Executing query: %s", select_statement.as_string(self.cursor))

        try:
            # Execute the query
            self.execute_statement(select_statement, (datasource_id, lags))
            result = self.cursor.fetchall()

            # Convert the result to a DataFrame
            df = pd.DataFrame(result, columns=['datasource_id', 'ts', 'value'])
            return df[['ts', 'value']]
        except Exception as e:
            logger.error(f"An error occurred: {e}")
            return pd.DataFrame(columns=['ts', 'value'])

    def create_data_sources_table(self):
        logger.info(f"Creating data sources table")

        table_name = self.config['database']['data-sources-table-name']
        create_statement = f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
                datasource_id INT NOT NULL,
                ts TIMESTAMP NOT NULL,
                value DOUBLE PRECISION  NULL
            );
        '''

        try:
            self.execute_statement(create_statement)
        except Exception as e:
            logger.error(f"An error occurred while creating the table: {e}")
            
    def create_datasource_forecasting_table(self):
        logger.info(f"Creating datasource forecasting table")

        table_name = self.config['database']['forecasting-table-name']
        create_statement = f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
                datasource_id INT NOT NULL,
                ts TIMESTAMP NOT NULL,
                algorithm varchar NOT NULL,
                value DOUBLE PRECISION NOT NULL
            );
        '''

        try:
            self.execute_statement(create_statement)
        except Exception as e:
            logger.error(f"An error occurred while creating the table: {e}")
    
    def insert_forecasting_dataframe(self, df: pd.DataFrame, ds_id: int, algorithm: str):
        logger.info(f'Inserting forecasting data for data source ID: {ds_id}')
        table_name = self.config['database']['forecasting-table-name']
        data_length = len(df)
        logger.info(f'Data length: {data_length}')

        for index, row in enumerate(df.to_dict(orient='records')):
            ts = row['ts']
            value = row['value']
            # logger.info(f'Processing row {index} with ts={ts} and value={value}')

            # Check if the record exists
            check_query = sql.SQL("""
                SELECT COUNT(*) FROM {}
                WHERE datasource_id = %s
                AND algorithm = %s
                AND ts = %s
            """).format(sql.Identifier(table_name))

            # logger.info('Executing check query')
            self.execute_statement(check_query, (ds_id, algorithm, ts))
            result = self.cursor.fetchone()
            exists = result[0] > 0 if result else False
            # logger.info(f'Record exists: {exists}')

            if exists:
                # Update existing record
                update_statement = sql.SQL("""
                    UPDATE {}
                    SET value = %s
                    WHERE datasource_id = %s
                    AND algorithm = %s
                    AND ts = %s
                """).format(sql.Identifier(table_name))

                # logger.info('Executing update statement')
                self.execute_statement(update_statement, (value, ds_id, algorithm, ts))
            else:
                # Insert new record
                insert_statement = sql.SQL("""
                    INSERT INTO {} (datasource_id, algorithm, ts, value)
                    VALUES (%s, %s, %s, %s)
                """).format(sql.Identifier(table_name))

                # logger.info('Executing insert statement')
                self.execute_statement(insert_statement, (ds_id, algorithm, ts, value))
                
            if index % 10 == 0:
                yield index, data_length

        logger.info('Finished inserting forecasting data')

    def get_forecasting_data_for_datasource(self, ds_id: int) -> pd.DataFrame:
        logger.info(f"Retrieving all data for data source ID: {ds_id}")

        table_name = self.config['database']['forecasting-table-name']
        select_statement = sql.SQL("SELECT * FROM {table} WHERE datasource_id = %s ORDER BY ts").format(
            table=sql.Identifier(table_name)
        )
        logger.info("Executing query: %s", select_statement.as_string(self.cursor))

        try:
            self.execute_statement(select_statement, (ds_id,))
            result = self.cursor.fetchall()

            # Convert the result to a DataFrame
            df = pd.DataFrame(result, columns=['datasource_id', 'ts', 'algorithm', 'value'])
            return df[['ts', 'algorithm', 'value']]
        except Exception as e:
            logger.error(f"An error occurred while retrieving all data: {e}")
            return pd.DataFrame(columns=['ts', 'algorithm', 'value'])