"""
Created on 2024-03-16

@author: wf
"""
from lodstorage.query import  QueryManager
from sqlmodel import Session, create_engine
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
    
    def __init__(self,clazz,sparql,sql_db,query_name: str,debug:bool=False):
        """
        Initializes the Manager with the given endpoint, cache name, and query name.

        Args:
            clazz: the type of the entities to manage
            sparql: The SPARQL endpoint for queries.
            query_name (str): The name of the query to execute.
        """
        self.clazz=clazz
        self.sparql=sparql
        self.sql_db=sql_db
        self.query_name = query_name
        self.debug=debug
        clazz.metadata.create_all(self.sql_db.engine)
        
    def get_lod(self,qm:QueryManager):
        query=qm.queriesByName[self.query_name]
        self.lod=self.sparql.queryAsListOfDicts(query.query)
        if self.debug:
            print(f"found {len(self.lod)} records for {self.query_name}")
  
    def store(self):
        profiler=Profiler(self.query_name,profile=self.debug)
        self.entities = [self.clazz.parse_obj(record) for record in self.lod]
        with self.sql_db.get_session() as session:
            session.add_all(self.entities)
            session.commit()   
        profiler.time()