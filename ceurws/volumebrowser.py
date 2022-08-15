'''
Created on 2022-08-14

@author: wf
'''
import re
from datetime import datetime

import justpy as jp
from jpwidgets.bt5widgets import Alert, App, Link
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
    
    def getValue(self,obj,attr):
        value=getattr(obj,attr,"?")
        if value is None:
            value="?"
        return value
            
class VolumesDisplay(Display):
    '''
    display all Volumes
    '''
    
    def __init__(self, app, container, debug:bool=False):
        '''
        constructor
        '''
        self.app=app
        self.debug=debug
        self.container = jp.Div(classes="container", a=container)
        self.rowA = jp.Div(classes="row", a=self.container)
        self.colA1 = jp.Div(classes="col-12", a=self.rowA)
        self.rowB = jp.Div(classes="row", a=self.container)
        self.colB1 = jp.Div(classes="col-12", a=self.rowB)
        try:
            self.agGrid=LodGrid(a=self.colB1)
            self.wdSync=WikidataSync()
            lod=[]
            volumeList=self.wdSync.vm.getList()
            limitTitleLen=120
            reverseVolumeList=sorted(volumeList, key=lambda volume:volume.number, reverse=True)
            for volume in reverseVolumeList:
                validMark= "✅" if volume.valid else "❌"
                lod.append(
                    {
                        "Vol": self.createLink(volume.url,f"Vol-{volume.number:04}"),
                        "Acronym": self.getValue(volume,"acronym"),
                        "Title": self.getValue(volume,"title")[:limitTitleLen],
                        "Loctime": self.getValue(volume,"loctime"),
                        "Published": self.getValue(volume,"published"),
                        "valid": validMark
                    }
                )  
            self.agGrid.load_lod(lod)
            self.agGrid.options.defaultColDef.resizable=True
            self.agGrid.options.defaultColDef.sortable=True
            self.agGrid.options.columnDefs[0].checkboxSelection = True
            self.agGrid.options.columnDefs[2].autoHeight=True
            self.agGrid.html_columns=[0,1,2]
            self.agGrid.on('rowSelected', self.onRowSelected)
        except Exception as ex:
            self.app.handleException(ex)

    def onRowSelected(self, msg):
        '''
        row selection event handler

        Args:
            msg(dict): row selection information
        '''
        if msg.get("selected", False):
            data = msg.get("data")
            volPattern = "http://ceur-ws.org/Vol-(?P<volumeNumber>\d{1,4})/"
            match = re.search(volPattern, data.get("Vol"))
            volumeId = int(match.group("volumeNumber")) if match is not None else None
            if volumeId is not None and volumeId in self.wdSync.volumesByNumber:
                volume: Volume = self.wdSync.volumesByNumber.get(volumeId)
                # check if already in wikidata → use URN
                urn = getattr(volume, "urn")
                wdItems = self.wdSync.getProceedingWdItemsByUrn(urn)
                if len(wdItems) > 0:
                    # a proceeding exists with the URN exists
                    alert = Alert(a=self.colA1, text=f"{volume} already in Wikidata see ")
                    for wdItem in wdItems:
                        jp.Br(a=alert)
                        qId = wdItem.split("/")[-1]
                        jp.Link(a=alert, href=wdItem, text=qId)
                    return
                else:
                    # A proceeding to the URN is not known → create wd entry
                    record = {
                        "title": getattr(volume, "title"),
                        "label": getattr(volume, "title"),
                        "description": f"Proceedings of {getattr(volume, 'acronym')} workshop",
                        "urn": getattr(volume, "urn"),
                        "short name": getattr(volume, "acronym"),
                        "volume": getattr(volume, "number"),
                        "pubDate": getattr(volume, "pubDate"),
                        "ceurwsUrl": getattr(volume, "url"),
                        "fullWorkUrl": getattr(volume, "url")
                    }
                    if isinstance(record.get("pubDate"), datetime):
                        record["pubDate"] = record["pubDate"].isoformat()
                    qId, errors = self.wdSync.addProceedingToWikidata(record)
                    if qId is not None:
                        alert = Alert(a=self.colA1, text=f"Proceedings entry for {volume} was created!")
                        jp.Br(a=alert)
                        qId = qId.split("/")[-1]
                        jp.Link(a=alert, href=qId, text=qId)
                    else:
                        alert = Alert(a=self.colA1, text=f"An error occured during the creation of the proceedings entry for {volume}")
                        jp.Br(a=alert)
                        jp.P(a=alert, text=errors)
            else:
                Alert(a=self.colA1, text=f"Volume for selected row can not be loaded correctly")
    
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
    
    def createItemLink(self,row,key):
        '''
        
        '''
        if key in row:
            item=row[key]
            itemLabel=row[f"{key}Label"]
            itemLink=self.createLink(item,itemLabel)
        else:
            itemLink="?"
        return itemLink
    
    def reloadAgGrid(self,olod:list,showLimit=10):
        '''
        reload the given grid
        '''
        if self.debug:
            pprint.pprint(olod[:showLimit])
        if self.agGrid is None:
            self.agGrid=LodGrid(a=self.app.rowB) 
        reverseLod=sorted(olod, key=lambda row: int(row["sVolume"]) if "sVolume" in row else int(row["Volume"]), reverse=True)
        lod=[]
        for row in reverseLod:
            if "sVolume" in row:
                volume=row["sVolume"]
            if "Volume" in row:
                volume=row["Volume"]
            itemLink=self.createItemLink(row, "item")
            eventLink=self.createItemLink(row,"event")
            eventSeriesLink=self.createItemLink(row, "eventSeries")
            volumeLink=self.createLink(f"http://ceur-ws.org/Vol-{volume}", f"Vol-{volume}")
            lod.append(
                {
                    "item": itemLink,
                    "volume": volumeLink,
                    "event": eventLink,
                    "series": eventSeriesLink,
                    "ordinal": row.get("eventSeriesOrdinal","?"),
                    "acronym":row.get("short_name","?"),
                    "title":row.get("title","?"),
                })
        self.agGrid.load_lod(lod)
        self.agGrid.options.defaultColDef.resizable=True
        self.agGrid.options.columnDefs[0].checkboxSelection = True
        self.agGrid.options.columnDefs[1].autoHeight=True
        self.agGrid.html_columns=[0,1,2,3]
    
  
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
        self.volumeDisplay=VolumesDisplay(self, container=self.colA1)
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