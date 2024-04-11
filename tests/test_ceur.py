"""
Created on 2024-03-17

@author: wf
"""
from tests.basetest import Basetest
from ceurws.models.ceur import Volume, Paper
from ceurws.sql_cache import SqlDB
from ceurws.ceur_ws import CEURWS
from sqlmodel import select  # Added 'select' here

class TestCEUR(Basetest):
    """
    tests CEUR-WS SQLmodel data caching
    """
    
    def setUp(self, debug=True, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)
        self.sql_db = SqlDB(CEURWS.CACHE_FILE, debug=False)
        
    def testCEUR(self):
        """
        test CEUR tables
        """
        for clazz in Paper, Volume:
            entity_plural_name=clazz.__tablename__
            clazz.metadata.create_all(self.sql_db.engine)
            # Attempt to read volumes from the database.
            with self.sql_db.get_session() as session:
                instances = session.exec(select(clazz)).all()
            
            # You can replace this assertion with more specific tests as needed.
            self.assertIsNotNone(instances, f"Failed to retrieve {entity_plural_name} from the database")
            if self.debug:
                print(f"Retrieved {len(instances)} {entity_plural_name} from the database")

        
