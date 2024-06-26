"""
Created on 2024-03-16
@author: wf
"""

from typing import Any

from lodstorage.query import QueryManager
from lodstorage.sparql import SPARQL
from ngwidgets.profiler import Profiler
from sqlmodel import Session, create_engine, select


class SqlDB:
    """
    general SQL database
    """

    def __init__(self, sqlite_file_path: str, debug: bool = False):
        debug = debug
        sqlite_url = f"sqlite:///{sqlite_file_path}"
        connect_args = {"check_same_thread": False}
        self.engine = create_engine(sqlite_url, echo=debug, connect_args=connect_args)

    def get_session(self) -> Session:
        """
        Provide a session for database operations.

        Returns:
            Session: A SQLAlchemy Session object bound to the engine for database operations.
        """
        return Session(bind=self.engine)


class Cached:
    """
    Manage cached entities.
    """

    def __init__(
        self, clazz: type[Any], sparql: SPARQL, sql_db: SqlDB, query_name: str, max_errors: int = 0, debug: bool = False
    ):
        """
        Initializes the Manager with class reference, SPARQL endpoint URL, SQL database connection string,
        query name, and an optional debug flag.
        Args:
            clazz (type[Any]): The class reference for the type of objects managed by this manager.
            sparql (SPARQL): a SPARQL endpoint.
            sql_db (SqlDB): SQL database object
            query_name (str): The name of the query to be executed.
            debug (bool, optional): Flag to enable debug mode. Defaults to False.
        """
        self.clazz = clazz
        self.sparql = sparql
        self.sql_db = sql_db
        self.query_name = query_name
        self.max_errors = max_errors
        self.debug = debug
        self.entities: list[object] = []
        self.errors: list[Exception] = []
        # Ensure the table for the class exists
        clazz.metadata.create_all(self.sql_db.engine)

    def fetch_or_query(self, qm, force_query=False):
        """
        Fetches data from the local cache if available.
        If the data is not in the cache or if force_query is True,
        it queries via SPARQL and caches the results.

        Args:
            qm (QueryManager): The query manager object used for making SPARQL queries.
            force_query (bool, optional): A flag to force querying via SPARQL even
                if the data exists in the local cache. Defaults to False.
        """
        if not force_query and self.check_local_cache():
            self.fetch_from_local()
        else:
            self.get_lod(qm)
            self.store()

    def check_local_cache(self) -> bool:
        """
        Checks if there is data in the local cache (SQL database).

        Returns:
            bool: True if  there is at least one record in the local SQL cache table
        """
        with self.sql_db.get_session() as session:
            result = session.exec(select(self.clazz)).first()
            return result is not None

    def fetch_from_local(self):
        """
        Fetches data from the local SQL database.
        """
        profiler = Profiler(f"fetch {self.query_name} from local", profile=self.debug)
        with self.sql_db.get_session() as session:
            self.entities = session.exec(select(self.clazz)).all()
            self.lod = [entity.dict() for entity in self.entities]
            if self.debug:
                print(f"Loaded {len(self.entities)} records from local cache")
        profiler.time()

    def get_lod(self, qm: QueryManager) -> list[dict]:
        """
        Fetches data using the SPARQL query specified by my query_name.

        Args:
            qm (QueryManager): The query manager object used for making SPARQL queries.
        Returns:
            list[dict]: A list of dictionaries representing the data fetched.
        """
        profiler = Profiler(f"fetch {self.query_name} from SPARQL endpoint {self.sparql.url}", profile=self.debug)
        query = qm.queriesByName[self.query_name]
        self.lod = self.sparql.queryAsListOfDicts(query.query)
        profiler.time()
        if self.debug:
            print(f"Found {len(self.lod)} records for {self.query_name}")
        return self.lod

    def to_entities(self, max_errors: int | None = None) -> list[Any]:
        """
        Converts records fetched from the LOD into entity instances, applying validation.
        Args:
            max_errors (int, optional): Maximum allowed validation errors. Defaults to 0.
        Returns:
            list[Any]: A list of entity instances that have passed validation.
        """
        self.entities = []
        self.errors = []
        error_records = []
        if max_errors is None:
            max_errors = self.max_errors
        for record in self.lod:
            try:
                entity = self.clazz.model_validate(record)
                self.entities.append(entity)
            except Exception as e:
                self.errors.append(e)
                error_records.append(record)
        error_count = len(self.errors)
        if error_count > max_errors:
            msg = f"found {error_count} errors > maximum allowed {max_errors} errors"
            if self.debug:
                print(msg)
                for i, error in enumerate(self.errors):
                    print(f"{i}:{error} for \n{error_records[i]}")
            raise Exception(msg)
        return self.entities

    def store(self, max_errors: int | None = None) -> list[Any]:
        """
        Stores the fetched data into the local SQL database.

        Args:
            max_errors (int, optional): Maximum allowed validation errors. Defaults to 0.
        Returns:
            list[Any]: A list of entity instances that were stored in the database.

        """
        profiler = Profiler(f"store {self.query_name}", profile=self.debug)
        self.to_entities(max_errors=max_errors)
        with self.sql_db.get_session() as session:
            session.add_all(self.entities)
            session.commit()
            if self.debug:
                print(f"Stored {len(self.entities)} records in local cache")
        profiler.time()
        return self.entities
