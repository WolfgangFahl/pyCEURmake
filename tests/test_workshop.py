'''
Created on 2020-11-22

@author: wf
'''
import unittest
from ceurws.workshop import Workshop

class TestWorkshop(unittest.TestCase):
    '''
    test workshop XML  handling
    '''


    def setUp(self):
        pass


    def tearDown(self):
        pass


    def testWorkshop(self):
        '''
        test reading a workshop xml file
        '''
        uri="https://raw.githubusercontent.com/semstats/semstats.github.io/master/2019/ceur/workshop.xml"
        workshop=Workshop.ofURI(uri)
        print (workshop.wsdict)
        pass


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()