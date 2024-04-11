"""
Created on 2024-03-16

@author: wf
"""

from tests.basetest import Basetest
from lodstorage.sparql import SPARQL
import os
from lodstorage.query import QueryManager
from lodstorage.sql_cache import Cached, SqlDB


class TestDblpCache(Basetest):
    """tests Dblp data caching"""

    def setUp(self, debug=True, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)
        # self.endpointUrl = "http://dblp.wikidata.dbis.rwth-aachen.de/api/dblp"
        self.endpoint_url = "https://qlever.cs.uni-freiburg.de/api/dblp"
        self.sparql = SPARQL(self.endpoint_url)
        self.force_query = True
        path = os.path.dirname(__file__)
        self.qYamlFile = os.path.join(
            os.path.dirname(path), "ceurws/resources/queries/dblp.yaml"
        )
        if os.path.isfile(self.qYamlFile):
            self.qm = QueryManager(lang="sparql", queriesPath=self.qYamlFile)
        self.db_path = "/tmp/ceurws.db"
        if self.force_query and os.path.isfile(self.db_path):
            os.remove(self.db_path)
        self.sql_db = SqlDB(self.db_path, debug=False)

    def test_dblp_caches(self):
        """
        test the dblp caches
        """
        from ceurws.models.dblp2 import (
            Paper,
            Scholar,
            Proceeding,
            Authorship,
            Editorship,
        )

        caches = [
            Cached(
                Proceeding,
                self.sparql,
                sql_db=self.sql_db,
                query_name="CEUR-WS-Volumes",
                max_errors=1,
                debug=self.debug,
            ),
            Cached(
                Scholar,
                self.sparql,
                sql_db=self.sql_db,
                query_name="CEUR-WS-Scholars",
                debug=self.debug,
            ),
            Cached(
                Paper,
                self.sparql,
                sql_db=self.sql_db,
                query_name="CEUR-WS-Papers",
                debug=self.debug,
            ),
            Cached(
                Editorship,
                self.sparql,
                sql_db=self.sql_db,
                query_name="CEUR-WS-Editorship",
                debug=self.debug,
            ),
            Cached(
                Authorship,
                self.sparql,
                sql_db=self.sql_db,
                query_name="CEUR-WS-Authorship",
                debug=self.debug,
            ),
        ]
        for cache in caches:
            cache.fetch_or_query(self.qm, force_query=self.force_query)
        # paper_cache.get_lod(self.qm)
        # paper_cache.store()
