'''
Created on 2022-08-11

@author: wf
'''
from tests.basetest import Basetest
from ceurws.ceur_ws import VolumeManager, CEURWS
import datetime
from ceurws.indexparser import IndexHtmlParser
import logging
from lodstorage.lod import LOD

class TestIndexHtml(Basetest):
    '''
    Test reading the index HTML
    '''
    
    def setUp(self, debug=False, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)
        self.url= 'http://ceur-ws.org'
        
    def checkVolumes(self,volumes):
        volumeCount=len(volumes)
        print(f"{volumeCount} volumes found")
        for index,volume in enumerate(volumes.values()):
            volumeNumber=volume["number"]
            expectedVolumeNumber=volumeCount-index
            if volumeNumber!=expectedVolumeNumber:
                print (f'{expectedVolumeNumber:4}:{volumeNumber:4} {expectedVolumeNumber-volumeNumber}')
    
    def volumesAsCsv(self,volumes,minVolumeNumber,maxVolumeNumber):
        '''
        show the given range of volumes in CSV format
        '''
        for volume in volumes:
            if volume.number>=minVolumeNumber and volume.number<=maxVolumeNumber:
                print(f"{volume.number}\t{volume.acronym}\t{volume.desc}\t{volume.h1}\t{volume.title}\tQ1860\t{volume.published}\t{volume.urn}\t{volume.url}")
            
    def testVolumeManagerFromHtml(self):
        vm=VolumeManager()
        vm.loadFromIndexHtml(force=True)
        withStore=False
        if withStore:
            vm.store()
        
    def testDates(self):
        dateFormat='%d-%b-%Y'
        now=datetime.datetime.now()
        nows=now.strftime(dateFormat)
        print(f"testing {nows} with {dateFormat}")
        _pdate=datetime.datetime.strptime(nows, dateFormat)
        
        
    def testReadingHtml(self):
        '''
        test reading the HTML file
        '''
        debug=self.debug
        #debug=True
        if debug:
            logging.basicConfig(level=logging.DEBUG)
        vm=VolumeManager()
        htmlText=vm.getIndexHtml(force=False)
        indexParser=IndexHtmlParser(htmlText,debug=debug) 
        lineCount=len(indexParser.lines)
        self.assertTrue(lineCount>89500)
        if debug or self.inPublicCI():
            print(f"{lineCount} lines found in CEUR-WS index.html")
        #limit=10
        # volumes=indexParser.parse(limit=10,verbose=True)
        volumes=indexParser.parse()
        self.checkVolumes(volumes)
        
    def testVolumesAsCsv(self):
        '''
        test getting volumes from CSV
        '''
        vm=VolumeManager()
        vm.load()
        volumes=vm.getList()
        self.volumesAsCsv(volumes,3185,3186)       
        
    def testReadVolumePages(self):
        '''
        test reading the volume pages
        '''
        withStore=False
        vm=VolumeManager()
        vm.loadFromIndexHtml(force=withStore)
        volumesByNumber, _duplicates = LOD.getLookup(vm.getList(), 'number')
        debug=self.debug or withStore
        if self.inPublicCI():
            limit=10
        else:
            limit=len(volumesByNumber)+1
        for number in range(1,limit):
            volume=volumesByNumber[number]
            volume.extractValuesFromVolumePage()
            if debug and volume.valid:
                print(f"{volume.url}:{volume.acronym}:{volume.desc}:{volume.h1}:{volume.title}")
        if withStore:
            vm.store()