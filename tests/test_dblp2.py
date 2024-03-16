"""
Created on 2024-03-16

@author: wf
"""
from tests.basetest import Basetest
from lodstorage.sparql import SPARQL
import os
from lodstorage.query import  QueryManager
from ceurws.models.dblp2 import Paper
from ceurws.cache import Cached, SqlDB

class TestDblpCache(Basetest):
    """tests Dblp data caching"""
    
    def setUp(self, debug=True, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)
        #self.endpointUrl = "http://dblp.wikidata.dbis.rwth-aachen.de/api/dblp"
        self.endpoint_url="https://qlever.cs.uni-freiburg.de/api/dblp"
        self.sparql=SPARQL(self.endpoint_url)
        path = os.path.dirname(__file__)
        path = os.path.dirname(path)
        qYamlFile = f"{path}/ceurws/resources/queries/dblp.yaml"
        if os.path.isfile(qYamlFile):
            self.qm = QueryManager(lang="sparql", queriesPath=qYamlFile)
        self.sql_db=SqlDB("/tmp/ceurws.db",debug=self.debug)
      
    def test_dblp_caches(self):
        """
        test the dblp caches
        """
        paper_cache=Cached(Paper,self.sparql,sql_db=self.sql_db,query_name="CEUR-WS-Papers",debug=self.debug)
        paper_cache.get_lod(self.qm)
        paper_cache.store()       