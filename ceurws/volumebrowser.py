'''
Created on 2022-08-14

@author: wf
'''
import justpy as jp
from jpwidgets.bt5widgets import App
from ceurws.ceur_ws import  Volume
from ceurws.querydisplay import QueryDisplay
import sys
from ceurws.wikidatasync import WikidataSync
import pprint
from jpwidgets.widgets import LodGrid

class Version(object):
    '''
    Version handling for VolumBrowser
    '''
    name="CEUR-WS Volume Browser"
    version='0.0.1'
    date = '2022-08-14'
    updated = '2022-08-14'
    description='CEUR-WS Volume browser'
    authors='Wolfgang Fahl'
    license=f'''Copyright 2022 contributors. All rights reserved.

  Licensed under the Apache License 2.0
  http://www.apache.org/licenses/LICENSE-2.0

  Distributed on an "AS IS" basis without warranties
  or conditions of any kind, either express or implied.'''
    longDescription=f"""{name} version {version}
{description}

  Created by {authors} on {date} last updated {updated}"""
  
  
class VolumeSearch():
    '''
    volume search
    '''
    def __init__(self,app,a,volA,debug:bool=False):
        '''
        constructor
        
        Args:
            app(App): the justpy bootstrap5 app
            a(jp.Component): the ancestor component for the search
            volA(jp.Component): the ancestor component for the Volume detail display
            debug(bool): if True swith debugging on
        '''
        self.app=app
        self.debug=debug
        self.wdSync=WikidataSync()
        self.app.addMenuLink(text='Endpoint',icon='web',href=self.wdSync.endpointConf.website,target="_blank")
        self.volumeInput=self.app.createComboBox(labelText="Volume", a=a,placeholder='Please type here to search ...',size="120",change=self.onVolumeChange)
        for volume in self.wdSync.vm.getList():
            title=f"Vol-{volume.number}:{volume.title}"
            self.volumeInput.dataList.addOption(title,volume.number)
        self.volumeDiv=jp.Div(a=volA)
        
    def updateVolume(self,volume:Volume):
        '''
        update the volume info according to the search result
        
        Args:
            volume(Volume): the currently selected volume
        '''
        html=f"<a href='{volume.url}'>{volume.acronym}<a>:{volume.desc}:{volume.h1}:{volume.title}"
        self.volumeDiv.inner_html=html
        
            
    async def onVolumeChange(self,msg):
        '''
        there has been a search 
        '''
        try:
            volumeNumberStr=msg.value
            volumeNumber=None
            try:
                volumeNumber=int(volumeNumberStr)
            except ValueError as _ve:
                # ignore invalid values
                pass      
            if volumeNumber in self.wdSync.volumesByNumber:    
                volume=self.wdSync.volumesByNumber[volumeNumber]
                self.updateVolume(volume)
        except Exception as ex:
            self.app.handleException(ex)
            
class Display:
    '''
    generic Display
    '''
    
    def createLink(self,url,text):
        '''
        create a link from the given url and text
        
        Args:
            url(str): the url to create a link for
            text(str): the text to add for the link
        '''
        link=f"<a href='{url}' style='color:blue'>{text}</a>"
        return link
            
class VolumesDisplay(Display):
    '''
    display all Volumes
    '''
    
    def __init__(self,app,debug:bool=False):
        '''
        constructor
        '''
        self.app=app
        self.debug=debug
        try:
            self.agGrid=LodGrid(a=self.app.rowB) 
            self.wdSync=WikidataSync()
            lod=[]
            for volume in self.wdSync.vm.getList():
                lod.append(
                    {
                        "Vol": self.createLink(volume.url,f"Vol-{volume.number}"),
                        #"Acronym": volume.acronym,
                        "Title": volume.title
                    }
                )  
            self.agGrid.load_lod(lod)
            self.agGrid.options.defaultColDef.sortable=True
            self.agGrid.options.columnDefs[0].checkboxSelection = True
            self.agGrid.html_columns=[0,1]
        except Exception as ex:
            self.app.handleException(ex)
    
class WikidataDisplay(Display):
    '''
    display wiki data query results
    '''
    
    def __init__(self,app,debug:bool=False):
        self.app=app
        self.debug=debug
        self.agGrid=None
        self.wdSync=WikidataSync()
        self.app.addMenuLink(text='Endpoint',icon='web',href=self.wdSync.endpointConf.website,target="_blank")
        self.pdQueryDisplay=self.createQueryDisplay("Proceedings", self.app.rowA)
        self.wikidataRefreshButton=jp.Button(text="refresh wikidata",classes="btn btn-primary",a=self.app.colA1,click=self.onWikidataRefreshButtonClick)

    def createQueryDisplay(self,name,a)->QueryDisplay:
        '''
        Args:
            name(str): the name of the query
            a(jp.Component): the ancestor

        Returns:
            QueryDisplay: the created QueryDisplay
        '''
        filenameprefix=f"{name}"
        qd=QueryDisplay(app=self.app,name=name,a=a,filenameprefix=filenameprefix,text=name,sparql=self.wdSync.sparql,endpointConf=self.wdSync.endpointConf)
        return qd    
    
    async def onWikidataRefreshButtonClick(self,_msg):
        '''
        wikidata Refresh button has been clicked
        '''
        try:
            self.updateWikidata()
            await self.app.wp.update()
        except Exception as ex:
            self.app.handleException(ex)

    def updateWikidata(self):
        '''
        update Wikidata
        '''
        self.pdQueryDisplay.showSyntaxHighlightedQuery(self.wdSync.wdQuery)
        wdRecords=self.wdSync.update()
        self.app.showFeedback(f"found {len(wdRecords)} wikidata records")
        self.reloadAgGrid(wdRecords)
        pass
    
    
    def reloadAgGrid(self,olod:list,showLimit=10):
        '''
        reload the given grid
        '''
        if self.debug:
            pprint.pprint(olod[:showLimit])
        if self.agGrid is None:
            self.agGrid=LodGrid(a=self.app.rowB) 
        lod=[]
        for row in olod:
            if "sVolume" in row:
                volume=row["sVolume"]
            if "Volume" in row:
                volume=row["Volume"]
            itemLabel=row["itemLabel"]
            item=row["item"]
            itemLink=self.createLink(item,itemLabel)
            volumeLink=self.createLink(f"http://ceur-ws.org/Vol-{volume}", f"Vol-{volume}")
            lod.append(
                {
                    "item": itemLink,
                    "volume": volumeLink,
                    "acronym":row.get("short_name","?"),
                    "title":row.get("title","?"),
                    
                })
        self.agGrid.load_lod(lod)
        self.agGrid.options.columnDefs[0].checkboxSelection = True
        self.agGrid.html_columns=[0,1]
    
  
class VolumeBrowser(App):
    '''
    CEUR-WS Volume Browser
    '''

    def __init__(self,version):
        '''
        Constructor
        
        Args:
            version(Version): the version info for the app
        '''
        App.__init__(self, version,title="CEUR-WS Volume Browser")
        self.addMenuLink(text='Home',icon='home', href="/")
        self.addMenuLink(text='Volumes',icon='table-large',href="/volumes")
        self.addMenuLink(text='Wikidata Sync',icon='refresh-circle',href="/wikidatasync")
        self.addMenuLink(text='Settings',icon='cog',href="/settings")
        self.addMenuLink(text='github',icon='github', href="https://github.com/WolfgangFahl/pyCEURmake/issues/16")
        self.addMenuLink(text='Documentation',icon='file-document',href="https://ceur-ws.bitplan.com/index.php/Volume_Browser")
        self.addMenuLink(text='Source',icon='file-code',href="https://github.com/WolfgangFahl/pyCEURmake/blob/main/ceurws/volumebrowser.py")
        
        # Routes
        jp.Route('/settings',self.settings)
        jp.Route('/volumes',self.volumes)
        jp.Route('/wikidatasync',self.wikidatasync)
        
        
    def setupRowsAndCols(self):
        head="""<link rel="stylesheet" href="/static/css/md_style_indigo.css">
<link rel="stylesheet" href="/static/css/pygments.css">
"""
        self.wp=self.getWp(head)
        self.rowA=jp.Div(classes="row",a=self.contentbox)
        self.rowB=jp.Div(classes="row",a=self.contentbox)
        self.rowC=jp.Div(classes="row",a=self.contentbox)
        self.rowD=jp.Div(classes="row",a=self.contentbox)
        
        self.colA1=jp.Div(classes="col-12",a=self.rowA)
        self.colC1=jp.Div(classes="col-12",a=self.rowC)
        self.colD1=jp.Div(classes="col-12",a=self.rowD)
        
        self.feedback=jp.Div(a=self.colC1)
        self.errors=jp.Span(a=self.colD1,style='color:red')
        
    def showFeedback(self,html):
        self.feedback.inner_html=html
    
    async def wikidatasync(self):
        self.setupRowsAndCols()
        self.wikidataDisplay=WikidataDisplay(self,debug=True)
        return self.wp
        
    async def settings(self):
        '''
        settings
        '''
        self.setupRowsAndCols()
        return self.wp
    
    async def volumes(self):
        self.setupRowsAndCols()
        self.volumeDisplay=VolumesDisplay(self)
        return self.wp
    
    async def content(self):
        '''
        show the content
        '''
        self.setupRowsAndCols()
        self.volumeSearch=VolumeSearch(self,self.colA1,self.rowB)
        self.wdSync=self.volumeSearch.wdSync
        return self.wp
        
        
DEBUG = 1
if __name__ == "__main__":
    if DEBUG:
        sys.argv.append("-d")
    app=VolumeBrowser(Version)
    sys.exit(app.mainInstance())