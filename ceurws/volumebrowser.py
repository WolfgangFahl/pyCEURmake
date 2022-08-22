'''
Created on 2022-08-14

@author: wf
'''
import re
import justpy as jp
from jpwidgets.bt5widgets import Alert, App, IconButton, Switch, ProgressBar
from jpwidgets.widgets import LodGrid
from ceurws.ceur_ws import  Volume
from ceurws.querydisplay import QueryDisplay
from ceurws.wikidatasync import WikidataSync
from ceurws.template import TemplateEnv
import pprint
import sys

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
            

            
class Display:
    '''
    generic Display
    '''
    noneValue="-"
    
    def createLink(self,url,text):
        '''
        create a link from the given url and text
        
        Args:
            url(str): the url to create a link for
            text(str): the text to add for the link
        '''
        link=f"<a href='{url}' target='_blank' style='color:blue'>{text}</a>"
        return link
    
    def createExternalLink(self,row:dict,key:str,text:str,formatterUrl:str,emptyIfNone:bool=False):
        '''
        create an ExternalLink for the given row entry with the given key, text and formatterUrl
        
        Args:
            row(dict): the row to extract the value from
            key(str): the key
            text(str): the text to display for the link
            formatterUrl(str): the prefix for the url to use
        '''
        value=self.getRowValue(row, key)
        if value==Display.noneValue: return "" if emptyIfNone else Display.noneValue
        url=formatterUrl+value
        link=self.createLink(url, text)
        return link
    
    def createWikidataSpan(self,a,wdSync,qId:str,volume:Volume):
        '''
        create a Wikidata Export span
        
        Args:
            a(): ancestor
            qId(str): wikidata item Q Identifier
            volume(Volume): the Volume
        '''
        href=wdSync.itemUrl(qId)
        wdSpan=jp.Span(a=a)
        jp.Link(a=wdSpan, href=self.volume.url,text=f"{volume}:{volume.acronym}")
        jp.Link(a=wdSpan, href=href, text=f"{qId} ")
        return wdSpan
    
    def getValue(self,obj,attr):
        value=getattr(obj,attr,Display.noneValue)
        if value is None:
            value=Display.noneValue
        return value
    
    def getRowValue(self,row,key):
        value=None
        if key in row:
            value=row[key]
        if value is None:
            value=Display.noneValue
        return value
       
    def setDefaultColDef(self,agGrid):
        defaultColDef=agGrid.options.defaultColDef
        defaultColDef.resizable=True
        defaultColDef.sortable=True
        # https://www.ag-grid.com/javascript-data-grid/grid-size/
        defaultColDef.wrapText=True
        defaultColDef.autoHeight=True
        
    def addFitSizeButton(self,a):
        self.onSizeColumnsToFitButton=Switch(
            a=a,
            labelText="fit",
            checked=False
            #iconName='format-columns',
            #classes="btn btn-primary btn-sm col-1"
        )
        self.onSizeColumnsToFitButton.on("input",self.onSizeColumnsToFit)
        
    async def onSizeColumnsToFit(self,_msg:dict):   
        try:
            await self.agGrid.run_api('sizeColumnsToFit()', self.app.wp)
        except Exception as ex:
            self.app.handleException(ex)
            
class WikidataRangeImport(Display):
    '''
    import a range of volumes
    '''
    
    def __init__(self,app,a):
        self.app=app
        self.rowA=jp.Div(classes="row",a=a)
        self.rowB=jp.Div(classes="row",a=a)
        self.rowC=jp.Div(classes="row",a=a)
        self.rowD=jp.Div(classes="row",a=a)
        
        self.colA1=jp.Div(classes="col-3",a=self.rowA)
        self.colA2=jp.Div(classes="col-3",a=self.rowA)
        self.colA3=jp.Div(classes="col-3",a=self.rowA)
        self.colD1=jp.Div(classes="col-12",a=self.rowD)
        self.wdSync=WikidataSync(debug=self.app.debug)
        self.fromInput=self.app.createInput(labelText="from", placeholder="from",change=self.onChangeFrom, a=self.colA1)
        self.toValue=self.app.createInput(labelText="to", placeholder="to",change=self.onChangeTo, a=self.colA2)
        self.uploadButton=IconButton(a=self.colA3,iconName="upload-multiple",click=self.onUploadButtonClick,classes="btn btn-primary btn-sm col-1")
        self.progressBar = ProgressBar(a=self.rowC)
        
    def feedback(self,msg):
        self.rowB.inner_html=msg
        print(msg)
        
    def importVolume(self,volumeNumber,progress):
        '''
        import the given volume showing the given progress
        '''
        if volumeNumber in self.wdSync.volumesByNumber:
            volume=self.wdSync.volumesByNumber[volumeNumber]
            wdRecord=self.wdSync.getWikidataProceedingsRecord(volume)
            msg=f"Importing {volume} to wikidata"
            self.feedback(msg)
            qId,err=self.wdSync.addProceedingsToWikidata(wdRecord, write=True, ignoreErrors=False)
            if qId is not None:
                _importSpan=self.createWikidataSpan(a=self.colD1,wdSync=self.app.wdSync,qId=qId, volume=volume)
            else:
                self.app.feedback(f"error:{err}")
            self.progressBar.updateProgress(progress)
        
    async def onUploadButtonClick(self,_msg):
        self.app.clearErrors()
        step=-1 if self.fromVolume>=self.toVolume else 1
        total=(self.toVolume-self.fromVolume)/step+1
        count=0
        for volumeNumber in range(self.fromVolume,self.toVolume+step,step):
            count+=1
            try:
                self.importVolume(volumeNumber,count/total*100)
                await self.app.wp.update()
            except Exception as ex:
                self.app.handleException(ex)
        
    async def onChangeFrom(self,msg):
        self.fromVolume=int(msg.value)
        
    async def onChangeTo(self,msg):
        self.toVolume=int(msg.value)
        
class VolumeDisplay(Display):
    '''
    displays a single volume
    '''
    def __init__(self,app,volumeToolbar,volumeHeaderDiv,volumeDiv):
        '''
        constructor
        
        Args:
            app(App): The bootstrap 5 app
            volnumber(int): the volume number 
            volumeToolbar(jp.Div): the div for the toolbar
            volumeHeaderDiv(jp.Div): the div for the header
            volumeDiv(jp.Div): the div for the volume content
        '''
        self.app=app
        self.volumeToolbar=volumeToolbar
        self.volumeHeaderDiv=volumeHeaderDiv
        self.volumeDiv=volumeDiv
        self.volumeRefreshButton=None
        self.wikidataButton=None
        self.volume=None
            
    def showVolume(self,volume):
        '''
        show the given volume
        
        Args:
            volume(Volume): the volume to show
        '''
        try:
            self.volume=volume
            if self.volumeRefreshButton is None:
                self.volumeRefreshButton=IconButton(
                    iconName="refresh",
                    title="Refresh from CEUR-WS Volume page",
                    classes="btn btn-primary btn-sm col-1",
                    a=self.volumeToolbar,
                    click=self.onRefreshButtonClick,
                )
            if self.wikidataButton is None:
                self.wikidataButton=IconButton(
                    iconName="web",
                    title="Export to Wikidata",
                    classes="btn btn-primary btn-sm col-1",
                    a=self.volumeToolbar,
                    click=self.onWikidataButtonClick,
                )
            wdProc=self.app.wdSync.getProceedingsForVolume(volume.number)
            self.wikidataButton.disabled=wdProc is not None
            if wdProc is not None:
                itemLink=self.createLink(wdProc["item"], "wikidataitem")
            else:
                itemLink=""   
            dblpLink=self.createExternalLink(wdProc,"dblpEventId","dblp","https://dblp.org/db/",emptyIfNone=True)
            k10PlusLink=self.createExternalLink(wdProc, "ppnId", "k10plus", "https://opac.k10plus.de/DB=2.299/PPNSET?PPN=",emptyIfNone=True)
            links=""
            delim=""
            for link in [itemLink,dblpLink,k10PlusLink]:
                if link:
                    links+=delim+link
                    delim="&nbsp;"
  
            #template=self.templateEnv.getTemplate('volume_index_body.html')
            #html=template.render(volume=volume)
            headerHtml=f"""{links}<h3>{volume.h1}</h3>
    <a href='{volume.url}'>{volume.acronym}<a>
    {volume.title}<br>
    {volume.desc}
    published: {volume.pubDate}
    submitted By: {volume.submittedBy}"""
            iframeHtml=f"""
            <iframe src='{volume.url}' style='min-height: calc(100%); width: calc(100%);'></iframe>"""
            self.volumeHeaderDiv.inner_html=headerHtml
            self.volumeDiv.inner_html=iframeHtml
    
        except Exception as ex:
            self.app.handleException(ex)
            
    async def onRefreshButtonClick(self,_msg):
        try:
            self.volume.extractValuesFromVolumePage()
            _alert=Alert(a=self.volumeToolbar,text=f"updated from {self.volume.url}")
            self.showVolume(self.volume)
            self.app.wdSync.storeVolumes()
        except Exception as ex:
            self.app.handleException(ex)  
            
    async def onWikidataButtonClick(self,_msg):
        '''
        handle wikidata sync request
        '''
        try:
            wdRecord=self.app.wdSync.getWikidataProceedingsRecord(self.volume)
            qId,err=self.app.wdSync.addProceedingsToWikidata(wdRecord, write=True, ignoreErrors=False)
            if qId is not None:
                alert=Alert(a=self.volumeToolbar,text=f"wikidata export")
                _wdSpan=self.createWikidataSpan(a=alert,wdSync=self.app.wdSync,qId=qId, volume=self.volume)   
            else:
                self.app.feedback(f"error:{err}")
        except Exception as ex:
            self.app.handleException(ex)  

class VolumeSearch():
    '''
    volume search
    '''
    def __init__(self,app,volumeInputDiv,volumeDisplay:VolumeDisplay,debug:bool=False):
        '''
        constructor
        
        Args:
            app(App): the justpy bootstrap5 app
            volumeInputDiv(): the input Div
            debug(bool): if True swith debugging on
        '''
        self.app=app
        self.debug=debug
        self.wdSync=WikidataSync(debug=debug)
        self.app.addMenuLink(text='Endpoint',icon='web',href=self.wdSync.endpointConf.website,target="_blank")
        self.volumeInput=self.app.createComboBox(labelText="Volume", a=volumeInputDiv,placeholder='Please type here to search ...',size="120",change=self.onVolumeChange)
        for volume in self.wdSync.vm.getList():
            title=f"Vol-{volume.number}:{volume.title}"
            self.volumeInput.dataList.addOption(title,volume.number)
        self.volumeDisplay=volumeDisplay
        
    def updateVolume(self,volume:Volume):
        '''
        update the volume info according to the search result
        
        Args:
            volume(Volume): the currently selected volume
        '''
        self.volumeDisplay.showVolume(volume)

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
            
class VolumeListDisplay(Display):
    '''
    display all Volumes
    '''
    
    def __init__(self, app, container, debug:bool=False):
        '''
        constructor
        '''
        self.app=app
        self.debug=debug
        self.dryRun=True
        self.ignoreErrors=False 
        self.container = jp.Div(classes="container", a=container)
        self.rowA = jp.Div(classes="row", a=self.container)
        self.colA1 = jp.Div(classes="col-2", a=self.rowA)
        self.colA2 = jp.Div(classes="col-2", a=self.rowA)
        self.colA3 = jp.Div(classes="col-8", a=self.rowA)
        self.rowB = jp.Div(classes="row", a=self.container)
        self.colB1 = jp.Div(classes="col-12", a=self.rowB)
        self.dryRunButton=Switch(a=self.colA1,labelText="dry run",checked=self.dryRun,disable=True)
        self.dryRunButton.on("input",self.onChangeDryRun)
        self.ignoreErrorsButton=Switch(a=self.colA2,labelText="ignore errors",checked=self.ignoreErrors)
        self.ignoreErrorsButton.on("input",self.onChangeIgnoreErrors)
        self.addFitSizeButton(a=self.colA3)
     
        try:
            self.agGrid=LodGrid(a=self.colB1)
            self.wdSync=WikidataSync(debug=self.debug)
            lod=[]
            volumeList=self.wdSync.vm.getList()
            reverseVolumeList=sorted(volumeList, key=lambda volume:volume.number, reverse=True)
            for volume in reverseVolumeList:
                validMark= "✅" if volume.valid else "❌"
                lod.append(
                    {
                        "Vol": self.createLink(volume.url,f"Vol-{volume.number:04}"),
                        "Acronym": self.getValue(volume,"acronym"),
                        "Title": self.getValue(volume,"title"),
                        "Loctime": self.getValue(volume,"loctime"),
                        "Published": self.getValue(volume,"published"),
                        "SubmittedBy": self.getValue(volume,"submittedBy"),
                        "valid": validMark
                    }
                )  
            self.agGrid.load_lod(lod)
            self.setDefaultColDef(self.agGrid)
            self.agGrid.options.columnDefs[0].checkboxSelection = True
            self.agGrid.html_columns=[0,1,2]
            self.agGrid.on('rowSelected', self.onRowSelected)     
        except Exception as ex:
            self.app.handleException(ex)
            
    def onChangeDryRun(self,msg:dict):
        '''
        handle change of DryRun setting
        
        Args:
            msg(dict): the justpy message
        '''
        self.dryRun=msg.value
        
    async def onChangeIgnoreErrors(self,msg:dict):
        '''
        handle change of IgnoreErrors setting
        
        Args:
            msg(dict): the justpy message
        '''
        self.ignoreErrors=msg.value    

    async def onRowSelected(self, msg):
        '''
        row selection event handler

        Args:
            msg(dict): row selection information
        '''
        if msg.get("selected", False):
            try: 
                self.app.clearErrors()
                data = msg.get("data")
                volPattern = "http://ceur-ws.org/Vol-(?P<volumeNumber>\d{1,4})/"
                match = re.search(volPattern, data.get("Vol"))
                volumeId = int(match.group("volumeNumber")) if match is not None else None
                if volumeId is not None and volumeId in self.wdSync.volumesByNumber:
                    volume: Volume = self.wdSync.volumesByNumber.get(volumeId)
                    await self.createEventItemAndLinkProceedings(volume, msg)
                else:
                    Alert(a=self.colA3, text=f"Volume for selected row can not be loaded correctly")
            except Exception as ex:
                self.app.handleException(ex)

    async def createProceedingsItemFromVolume(self, volume: Volume, msg):
        """
        Create wikidata item for proceedings of given volume
        """
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
            # A proceedings volume for the URN is not known → create wd entry
            wdRecord = self.wdSync.getWikidataProceedingsRecord(volume)
            if self.dryRun:
                prettyData = pprint.pformat(msg.data)
                text = f"{prettyData}"
                alert = Alert(a=self.colA3, text=text)

            write = not self.dryRun
            qId, errors = self.wdSync.addProceedingsToWikidata(wdRecord, write=write, ignoreErrors=self.ignoreErrors)
            if qId is not None:
                alert = Alert(a=self.colA3, text=f"Proceedings entry for {volume} was created!")
                jp.Br(a=alert)
                href = self.wdSync.itemUrl(qId)
                jp.Link(a=alert, href=href, text=qId)
            else:
                alert = Alert(a=self.colA3,
                              text=f"An error occured during the creation of the proceedings entry for {volume}")
                jp.Br(a=alert)
                jp.P(a=alert, text=errors)

    async def createEventItemAndLinkProceedings(self, volume: Volume, msg):
        """Create event  wikidata item for given volume and link the proceedings with the event"""
        write = not self.dryRun
        volNumber = getattr(volume, "number")
        if self.wdSync.checkIfProceedingsFromExists(volNumber, eventItemQid=None):
            # link between proceedings and event already exists
            proceedingsWikidataId = self.wdSync.getWikidataIdByVolumeNumber(number=volNumber)
            alert = Alert(a=self.colA3, text=f"Vol-{volNumber}:Event and Link between proceedings and event already exists")
            jp.Br(a=alert)
            proceedings_href = self.wdSync.itemUrl(proceedingsWikidataId)
            jp.Link(a=alert, href=proceedings_href, text=proceedingsWikidataId)
            return
        dblpEntityIds = self.wdSync.dbpEndpoint.getDblpIdByVolumeNumber(volNumber)
        if len(dblpEntityIds) > 1:
            Alert(a=self.colA3, text=f"Multiple dblpEventIds found for Vol-{volNumber}: {','.join(dblpEntityIds)}")
            return
        elif len(dblpEntityIds) == 1:
            dblpEntityId = dblpEntityIds[0]
        else:
            dblpEntityId = None
        wdItems = self.wdSync.getWikidataIdByDblpEventId(dblpEntityId, volNumber)
        eventQid = None
        errors = None
        if len(wdItems) == 0:
            # event item does not exist → create a new one
            eventRecord = self.wdSync.getWikidataEventRecord(volume)
            self.wdSync.login()
            eventQid, errors = self.wdSync.doAddEventToWikidata(record=eventRecord, write=write)
            self.wdSync.logout()
        elif len(wdItems) == 1:
            # the event item already exists
            eventQid = wdItems[0]
        else:
            alert = Alert(a=self.colA3, text=f"For the volume {volNumber} multiple event entries exist:")
            jp.Br(a=alert)
            for qId in wdItems:
                href = self.wdSync.itemUrl(qId)
                jp.Link(a=alert, href=href, text=qId)
            return
        if eventQid is not None:
            # add link between Proceedings and the event item
            self.wdSync.login()
            proceedingsWikidataId, errors = self.wdSync.addLinkBetweenProceedingsAndEvent(volumeNumber=volNumber, eventItemQid=eventQid, write=write)
            self.wdSync.logout()
            alert = Alert(a=self.colA3, text="")
            event_href = self.wdSync.itemUrl(eventQid)
            jp.Link(a=alert, href=event_href, text=f"Event entry for {volume}: {eventQid}")
            jp.Br(a=alert)
            proceedings_href = self.wdSync.itemUrl(proceedingsWikidataId)
            jp.Link(a=alert, href=proceedings_href, text=f"Proceedings entry for {volume}: {proceedingsWikidataId}")

        else:
            alert = Alert(a=self.colA3, text=f"An error occured during the creation of the proceedings entry for {volume}")
            jp.Br(a=alert)
            jp.P(a=alert, text=errors)

    
class WikidataDisplay(Display):
    '''
    display wiki data query results
    '''
    def __init__(self,app,debug:bool=False):
        self.app=app
        self.debug=debug
        self.agGrid=None
        self.wdSync=WikidataSync(debug=debug)
        self.app.addMenuLink(text='Endpoint',icon='web',href=self.wdSync.endpointConf.website,target="_blank")
        self.pdQueryDisplay=self.createQueryDisplay("Proceedings", self.app.rowA)
        self.readProceedingsButton=jp.Button(text="from cache",classes="btn btn-primary",a=self.app.colA1,click=self.onReadProceedingsClick)
        self.wikidataRefreshButton=jp.Button(text="refresh wikidata",classes="btn btn-primary",a=self.app.colA1,click=self.onWikidataRefreshButtonClick)
        self.addFitSizeButton(a=self.app.colA1)

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
    
    async def onReadProceedingsClick(self,_msg):
        '''
        read Proceedings button has been clicked
        '''
        try:
            proceedingsRecords=self.wdSync.loadProceedingsFromCache()
            self.app.showFeedback(f"found {len(proceedingsRecords)} cached wikidata proceedings records")
            self.reloadAgGrid(proceedingsRecords)
            await self.app.wp.update()
        except Exception as ex:
            self.app.handleException(ex)
    
    async def onWikidataRefreshButtonClick(self,_msg):
        '''
        wikidata Refresh button has been clicked
        '''
        try:
            _alert=Alert(a=self.app.colA1,text="running SPARQL query to retrieve CEUR-WS proceedings from Wikidata ...")
            await self.app.wp.update()
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
        _alert=Alert(a=self.app.colA1,text=f"found {len(wdRecords)} wikidata CEUR-WS proceedings records")
        self.reloadAgGrid(wdRecords)
        pass
    
    def createItemLink(self,row,key):
        '''
        create an item link
        '''
        value=self.getRowValue(row, key)
        if value==Display.noneValue: return value
        item=row[key]
        itemLabel=row[f"{key}Label"]
        itemLink=self.createLink(item,itemLabel)
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
            volume=self.getRowValue(row, "sVolume")
            if volume=="?":
                volume=self.getRowValue(row, "Volume")
            volNumber="?"
            if volume!="?":
                volNumber=int(volume)
                volumeLink=self.createLink(f"http://ceur-ws.org/Vol-{volume}", f"Vol-{volNumber:04}")
            else:
                volumeLink="?"   
            itemLink=self.createItemLink(row, "item")
            eventLink=self.createItemLink(row,"event")
            eventSeriesLink=self.createItemLink(row, "eventSeries")
            #@TODO - use formatterUris from Wikidata
            dblpLink=self.createExternalLink(row,"dblpEventId","dblp","https://dblp.org/db/")
            k10PlusLink=self.createExternalLink(row, "ppnId", "k10plus", "https://opac.k10plus.de/DB=2.299/PPNSET?PPN=")
            lod.append(
                {
                    "item": itemLink,
                    "volume": volumeLink,
                    "acronym": self.getRowValue(row, "short_name"),
                    "dblp": dblpLink,
                    "k10plus": k10PlusLink,
                    "event": eventLink,
                    "series": eventSeriesLink,
                    "ordinal": self.getRowValue(row,"eventSeriesOrdinal"),

                   # "title":row.get("title","?"),
                })
        self.agGrid.load_lod(lod)
        self.setDefaultColDef(self.agGrid)
        self.agGrid.options.columnDefs[0].checkboxSelection = True
        self.agGrid.html_columns=[0,1,2,3,4,5,6]
  
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
        self.addMenuLink(text='github',icon='github', href="https://github.com/WolfgangFahl/pyCEURmake/issues/16",target="_blank")
        self.addMenuLink(text='Documentation',icon='file-document',href="https://ceur-ws.bitplan.com/index.php/Volume_Browser",target="_blank")
        self.addMenuLink(text='Source',icon='file-code',href="https://github.com/WolfgangFahl/pyCEURmake/blob/main/ceurws/volumebrowser.py",target="_blank")
        
        # Routes
        jp.Route('/settings',self.settings)
        jp.Route('/volumes',self.volumes)
        jp.Route('/volume/{volnumber}',self.volumePage)
        jp.Route('/wikidatasync',self.wikidatasync)
        self.templateEnv=TemplateEnv()
        
    def setupPage(self,header=""):
        header="""<link rel="stylesheet" href="/static/css/md_style_indigo.css">
<link rel="stylesheet" href="/static/css/pygments.css">
"""+header
        self.wp=self.getWp(header)  
        
    def setupRowsAndCols(self,header=""):
        self.setupPage(header)
        self.rowA=jp.Div(classes="row",a=self.contentbox)
        self.rowB=jp.Div(classes="row",a=self.contentbox)
        self.rowC=jp.Div(classes="row min-vh-100 vh-100",a=self.contentbox)
        self.rowD=jp.Div(classes="row",a=self.contentbox)
        
        self.colA1=jp.Div(classes="col-12",a=self.rowA)
        self.colC1=jp.Div(classes="col-12",a=self.rowC)
        self.colD1=jp.Div(classes="col-12",a=self.rowD)
        
        self.feedback=jp.Div(a=self.colD1)
        self.errors=jp.Span(a=self.colD1,style='color:red')
        
    def showFeedback(self,html):
        self.feedback.inner_html=html
    
    async def wikidatasync(self):
        self.setupRowsAndCols()
        self.wikidataDisplay=WikidataDisplay(self,debug=self.debug)
        return self.wp
        
    async def settings(self):
        '''
        settings
        '''
        self.setupRowsAndCols()
        #self.wdRangeImport=WikidataRangeImport(self,a=self.rowA)
        return self.wp
    
    async def volumePage(self,request):
        '''
        show a page for the given volume
        '''
        self.setupPage()
        self.rowA=jp.Div(classes="row",a=app.contentbox)
        self.rowB=jp.Div(classes="row min-vh-100 vh-100",a=app.contentbox)
        self.colA1=jp.Div(classes="col-12",a=self.rowA)   
        self.feedback=jp.Span(a=self.colA1)
        self.errors=jp.Span(a=self.colA1,style='color:red')
        if "volnumber" in request.path_params:
            volnumberStr=request.path_params["volnumber"]
        else:
            volnumberStr=None    
        volumeToolbar=jp.Div(a=self.rowA,classes="col-12")
        volumeHeaderDiv=jp.Div(a=self.rowA,classes="col-12")
        volumeDiv=self.rowB
        self.volumeDisplay=VolumeDisplay(self,volumeToolbar=volumeToolbar,volumeHeaderDiv=volumeHeaderDiv,volumeDiv=volumeDiv)
        self.wdSync=WikidataSync(self.debug)
        volume=None
        if volnumberStr:
            try:
                volnumber=int(volnumberStr)
                volume=self.wdSync.volumesByNumber[volnumber]
            except Exception as _ex:
                pass
        if volume:
            self.volumeDisplay.showVolume(volume)
        else:
            Alert(a=self.colA1,text=f"Volume display for {volnumber} failed")
        return self.wp
    
    async def volumes(self):
        '''
        show the volumes table
        '''
        self.setupRowsAndCols()
        self.volumeListDisplay=VolumeListDisplay(self, container=self.rowA ,debug=self.debug)
        return self.wp
    
    async def content(self):
        '''
        show the content
        '''
        self.setupRowsAndCols()
        volumeToolbar=jp.Div(a=self.rowB,classes="col-12")
        volumeHeaderDiv=jp.Div(a=self.rowB,classes="col-12")
        volumeDiv=self.rowC
        volumeDisplay=VolumeDisplay(self,volumeToolbar=volumeToolbar,volumeHeaderDiv=volumeHeaderDiv,volumeDiv=volumeDiv)
        self.volumeSearch=VolumeSearch(self,self.colA1,volumeDisplay)
        self.wdSync=self.volumeSearch.wdSync
        return self.wp
        
DEBUG = 1
if __name__ == "__main__":
    if DEBUG:
        sys.argv.append("-d")
    app=VolumeBrowser(Version)
    sys.exit(app.mainInstance())