'''
Created on 2023-03-21

@author: wf
'''
from tests.basetest import Basetest
from ceurws.namedqueries import NamedQueries
import json
import unittest

class TestNamedQueries(Basetest):
    '''
    Test reading the index HTML
    '''
     
    @unittest.skipIf(True, "Only for manual testing")
    def test_NamedQueries(self):
        """
        get generating named queries
        """
        nq=NamedQueries()
        nq.query()
        debug=True
        if debug:
            print(json.dumps(nq.q_records,indent=2,default=str))
        qm=nq.toQueryManager()
        yaml_str=nq.toYaml()
        if debug:
            print(yaml_str)
