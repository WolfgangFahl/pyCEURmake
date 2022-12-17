'''
Created on 2020-11-12

@author: wf
'''
from urllib.request import urlopen
import xmltodict

class Workshop(object):
    '''
    a single Workshop
    '''

    def __init__(self):
        '''
        Constructor
        '''

    @staticmethod
    def ofURI(uri):
        xml=urlopen(uri).read().decode()
        ws=Workshop()
        ws.wsdict=xmltodict.parse(xml)
        return ws
        