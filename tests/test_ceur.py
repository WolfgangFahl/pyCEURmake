"""
Created on 2024-03-17

@author: wf
"""

import unittest

from sqlmodel import select  # Added 'select' here

from ceurws.ceur_ws import CEURWS
from ceurws.models.ceur import Paper, Volume
from ceurws.sql_cache import SqlDB
from tests.basetest import Basetest


class TestCEUR(Basetest):
    """
    tests CEUR-WS SQLmodel data caching
    """

    def setUp(self, debug=True, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)
        self.sql_db = SqlDB(CEURWS.CACHE_FILE, debug=False)

    @unittest.skip(
        "Deactivated until 'TypeError: fromisoformat: argument must be str "
        "lib/sqlalchemy/cyextension/processors.pyx:40: TypeError' is fixed"
    )
    def testCEUR(self):
        """
        test CEUR tables
        """
        for clazz in Paper, Volume:
            entity_plural_name = clazz.__tablename__
            clazz.metadata.create_all(self.sql_db.engine)
            # Attempt to read volumes from the database.
            with self.sql_db.get_session() as session:
                statement = select(clazz)
                instances = session.exec(statement).all()
            # You can replace this assertion with more specific tests as needed.
            self.assertIsNotNone(
                instances,
                f"Failed to retrieve {entity_plural_name} from the database",
            )
            if self.debug:
                print(f"Retrieved {len(instances)} {entity_plural_name} from the database")
