"""
Created on 2024-03-16

@author: wf
"""
from lodstorage.query import  QueryManager
from sqlmodel import Session, create_engine, select
from ngwidgets.profiler import Profiler

class SqlDB:
    """
    general SQL database
    """
    def __init__(self, sqlite_file_path: str,debug:bool=False):
        debug=debug
        sqlite_url = f"sqlite:///{sqlite_file_path}"
        connect_args = {"check_same_thread": False}
        self.engine = create_engine(sqlite_url, echo=debug, connect_args=connect_args)
      
    def get_session(self):
        # Provide a session for database operations
        return Session(bind=self.engine)

class Cached:
    """
    Manage cached entities.
    """
    
    def __init__(self, clazz, sparql, sql_db, query_name: str, debug:bool=False):
        """
        Initializes the Manager with the given endpoint, cache name, and query name.
        """
        self.clazz = clazz
        self.sparql = sparql
        self.sql_db = sql_db
        self.query_name = query_name
        self.debug = debug
        # Ensure the table for the class exists
        clazz.metadata.create_all(self.sql_db.engine)
        
    def fetch_or_query(self, qm: QueryManager):
        """
        Fetches data from the local cache if available; otherwise, queries via SPARQL and caches the results.
        """
        if self.check_local_cache():
            self.fetch_from_local()
        else:
            self.get_lod(qm)
            self.store()
            
    def check_local_cache(self) -> bool:
        """
        Checks if there is data in the local cache (SQL database).
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
  
    def get_lod(self, qm: QueryManager):
        """
        Fetches data using the SPARQL query.
        """
        query = qm.queriesByName[self.query_name]
        self.lod = self.sparql.queryAsListOfDicts(query.query)
        if self.debug:
            print(f"Found {len(self.lod)} records for {self.query_name}")
  
    def store(self):
        """
        Stores the fetched data into the local SQL database.
        """
        profiler = Profiler(f"store {self.query_name}", profile=self.debug)
        self.entities = [self.clazz.parse_obj(record) for record in self.lod]
        with self.sql_db.get_session() as session:
            session.add_all(self.entities)
            session.commit()
            if self.debug:
                print(f"Stored {len(self.entities)} records in local cache")
        profiler.time()
