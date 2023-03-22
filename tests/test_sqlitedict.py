'''
Created on 2023-03-22

@author: wf
'''
from sqlitedict import SqliteDict

from tests.basetest import Basetest, Profiler
from ceurws.ceur_ws import CEURWS
import json
import os

class TestSqliteDict(Basetest):
    """
    test access to ceurws cache with SqliteDict
    """
    
    def test_sqlite_dict(self):
        """
        test volumes and papers
        """
        debug=True
        if os.path.isfile(CEURWS.CACHE_FILE):
            for tablename,pkey in [("volumes","number"),("papers","id")]:
                profiler=Profiler(tablename)
                sdict= SqliteDict(CEURWS.CACHE_FILE, tablename=tablename, decode=json.loads,autocommit=False)
                elapsed=profiler.time()
                if debug:
                    print(f"loaded {len(sdict)} {tablename} in {elapsed*1000:5.0f} msecs")
                profiler=Profiler(f"{tablename} by {pkey}")    
                lod_by_key={}
                for pkey,record in sdict.items():
                    lod_by_key[pkey]=record
                elapsed=profiler.time()
                if debug:
                    print(f"loaded {len(lod_by_key)} {tablename} by {pkey} in {elapsed*1000:5.0f} msecs")
                    
        