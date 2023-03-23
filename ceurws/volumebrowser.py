'''
Created on 2022-08-14

@author: wf
'''
import asyncio
import re
import time

import justpy as jp
from jpcore.justpy_app import JustpyApp
from jpwidgets.bt5widgets import About, Alert, App, IconButton, Switch, ProgressBar
from ceurws.ceur_ws import Volume
from ceurws.querydisplay import QueryDisplay
from ceurws.wikidatasync import DblpEndpoint, WikidataSync
from ceurws.template import TemplateEnv
import pprint
import sys
from ceurws.version import Version

class Display:
    """
    generic Display
    """
    noneValue = "-"

    def createLink(self, url: str, text: str):
        """
        create a link from the given url and text

        Args:
            url(str): the url to create a link for
            text(str): the text to add for the link
        """
        link = f"<a href='{url}' target='_blank' style='color:blue'>{text}</a>"
        return link

    def createExternalLink(self, row: dict, key: str, text: str, formatterUrl: str, emptyIfNone: bool = False) -> str:
        """
        create an ExternalLink for the given row entry with the given key, text and formatterUrl

        Args:
            row(dict): the row to extract the value from
            key(str): the key
            text(str): the text to display for the link
            formatterUrl(str): the prefix for the url to use
            emptyIfNone(bool): if True return empty string if value is Display.noneValue

        Returns:
            str - html link for external id
        """
        value = self.getRowValue(row, key)
        wdPrefix = "http://www.wikidata.org/entity/"
        if value.startswith(wdPrefix):
            value = value.replace(wdPrefix, "")
        if value == Display.noneValue:
            if emptyIfNone:
                return ""
            else:
                return Display.noneValue
        url = formatterUrl + value
        link = self.createLink(url, text)
        return link

    def createVolumeSpan(self,a,volume:Volume):
        '''
        create a Volume span linking to our local volume display

        Args:
            a(): ancestor
            volume(Volume): the Volume
        '''
        wdSpan=jp.Span(a=a)
        jp.Link(a=wdSpan, href=f"/volume/{volume.number}",text=f"{volume}:{volume.acronym}")
        space=jp.Span(a=wdSpan)
        space.inner_html="&nbsp;"
        return wdSpan

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

    def createEventProceedingsList(
            self,
            a,
            wdSync: WikidataSync,
            volume: Volume,
            proceedingsId: str = None,
            eventId: str = None,
            msg: str = None
    ):
        """
        Create an unordered horizontal list with the given ids
        """
        ul = jp.Ul(a=a, classes="list-group list-group-horizontal")
        li = jp.Li(a=ul, classes="list-group-item", text=f"Vol-{getattr(volume, 'number')}")
        li1 = jp.Li(a=ul, classes="list-group-item")
        if proceedingsId is not None:
            jp.Link(a=li1, href=wdSync.itemUrl(proceedingsId), text=proceedingsId)
        li2 = jp.Li(a=ul, classes="list-group-item")
        if eventId is not None:
            jp.Link(a=li2, href=wdSync.itemUrl(eventId), text=eventId)
        li3 = jp.Li(a=ul, classes="list-group-item", text=wdSync.getEventNameFromTitle(getattr(volume, "title")))
        li4 = jp.Li(a=ul, classes="list-group-item", text=msg)

    def getValue(self,obj,attr):
        value=getattr(obj,attr,Display.noneValue)
        if value is None:
            value=Display.noneValue
        return value

    def getRowValue(self, row, key):
        value=None
        if key in row:
            value=row[key]
        if value is None:
            value=Display.noneValue
        return value

    def setDefaultColDef(self, agGrid):
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
            await asyncio.sleep(0.2)
            if self.agGrid:
                await self.agGrid.run_api('sizeColumnsToFit()', self.app.wp)
        except Exception as ex:
            self.app.handleException(ex)

class VolumeListRefresh(Display):
    '''
    refresher for the list of volumes
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
        self.refreshButton=IconButton(a=self.colA1,iconName="upload-multiple",click=self.onRefreshButtonClick,classes="btn btn-primary btn-sm col-1")
        self.progressBar = ProgressBar(a=self.rowC)

    def updateRecentlyAddedVolume(self,volume,feedback,index,total):
        """
        update a recently added Volume
        
        Args:
            volume(Volume): the volume to update
            feedback: the div where to but the feedback message
            index(int): the relative index of the volume currently being added
            total(int): the total number of volumes currently being added
        """
        feedback.inner_html=f"reading {index}/{total} from {volume.url}"
        volume.extractValuesFromVolumePage()
        self.app.wdSync.addVolume(volume)
        self.progressBar.updateProgress(index/total*100)

    async def onRefreshButtonClick(self,_msg):
        '''
        handle clicking of the refresh button to get recently added volumes
        '''
        self.app.clearErrors()
        try:
            _alert=Alert(a=self.colA1,text="checking CEUR-WS index.html for recently added volumes ...")
            await self.app.wp.update()
            volumesByNumber,addedVolumeNumberList=self.app.wdSync.getRecentlyAddedVolumeList()
            _alert.inner_html=f"found {len(addedVolumeNumberList)} new volumes"
            total=len(addedVolumeNumberList)
            for i,volumeNumber in enumerate(addedVolumeNumberList):
                if i % 100 == 0 and i != 0:
                    self.app.wdSync.storeVolumes()
                    time.sleep(60)
                volume=volumesByNumber[volumeNumber]
                self.updateRecentlyAddedVolume(volume,_alert,i+1,total)
                _importSpan=self.createVolumeSpan(a=self.colD1,volume=volume)
                await self.app.wp.update()
            pass
            self.app.wdSync.storeVolumes()
            self.progressBar.updateProgress(0)

            _alert.inner_html="Done"
        except Exception as ex:
            _error=jp.Span(a=_alert,text="Error: {str(ex)}",style="color:red")
            self.app.handleException(ex)

class WikidataRangeImport(Display):
    """
    import a range of volumes
    """

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

    def importVolume(self, volume: Volume):
        """
        import the given volume showing the given progress
        """
        wdRecord=self.app.wdSync.getWikidataProceedingsRecord(volume)
        msg=f"Importing {volume} to wikidata"
        self.feedback(msg)
        qId,err=self.app.wdSync.addProceedingsToWikidata(wdRecord, write=True, ignoreErrors=False)
        if qId is not None:
            _importSpan=self.createWikidataSpan(a=self.colD1,wdSync=self.app.wdSync,qId=qId, volume=volume)
        else:
            self.app.feedback(f"error:{err}")

    def createEventItemAndLinkProceedings(self, volume: Volume):
        """
        Create event  wikidata item for given volume and link the proceedings with the event
        Args:
            volume: volume to create the event and proceedings link for
        """
        proceedingsQId, eventQId, msg = self.app.wdSync.doCreateEventItemAndLinkProceedings(volume, write=True)
        self.createEventProceedingsList(
                self.colD1,
                self.wdSync,
                volume=volume,
                proceedingsId=proceedingsQId,
                eventId=eventQId,
                msg=msg)

    async def onUploadButtonClick(self, _msg):
        self.app.clearErrors()
        step=-1 if self.fromVolume>=self.toVolume else 1
        total=(self.toVolume-self.fromVolume)/step+1
        count=0
        self.app.wdSync.login()
        for volumeNumber in range(self.fromVolume,self.toVolume+step,step):
            count+=1
            try:
                volume: Volume = self.app.wdSync.volumesByNumber.get(volumeNumber)
                if volume is not None:
                    try:
                        #self.importVolume(volume)
                        self.createEventItemAndLinkProceedings(volume)
                    except Exception as ex:
                        print(ex)
                        self.createEventProceedingsList(self.colD1, self.wdSync, volume,
                                                    msg=f"An error occured during the creation of the proceedings entry for {volume}")
                    finally:
                        self.progressBar.incrementProgress(100 / (total - 1))
                        print(f"Vol-{volumeNumber}")
                        await self.app.wp.update()
            except Exception as ex:
                self.app.handleException(ex)
        self.app.wdSync.logout()

    async def onChangeFrom(self,msg):
        self.fromVolume=int(msg.value)

    async def onChangeTo(self,msg):
        self.toVolume=int(msg.value)


class VolumeDisplay(Display):
    """
    displays a single volume
    """

    def __init__(self,app,volumeToolbar,volumeHeaderDiv,volumeDiv):
        """
        constructor

        Args:
            app(App): The bootstrap 5 app
            volnumber(int): the volume number
            volumeToolbar(jp.Div): the div for the toolbar
            volumeHeaderDiv(jp.Div): the div for the header
            volumeDiv(jp.Div): the div for the volume content
        """
        self.app=app
        self.volumeToolbar=volumeToolbar
        self.volumeHeaderDiv=volumeHeaderDiv
        self.volumeDiv=volumeDiv
        self.volumeRefreshButton=None
        self.wikidataButton=None
        self.volume=None

    def showVolume(self,volume):
        """
        show the given volume

        Args:
            volume(Volume): the volume to show
        """
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
            links=""
            if wdProc is not None:
                # wikidata proceedings link
                itemLink=self.createLink(wdProc["item"], "wikidataitem")
                # dblp proceedings link
                dblpLink=self.createExternalLink(wdProc,"dblpEventId","dblp",DblpEndpoint.DBLP_EVENT_PREFIX,emptyIfNone=True)
                # k10plus proceedings link
                k10PlusLink=self.createExternalLink(wdProc, "ppnId", "k10plus", "https://opac.k10plus.de/DB=2.299/PPNSET?PPN=",emptyIfNone=True)
                # scholia proceedings link
                scholiaLink=self.createExternalLink(wdProc, "item", "scholia", "https://scholia.toolforge.org/venue/", emptyIfNone=True)
                # scholia event link
                scholiaEventLink=self.createExternalLink(wdProc, "event", "event",  "https://scholia.toolforge.org/event/", emptyIfNone=True)
                # scholia event series link
                scholiaEventSeriesLink=self.createExternalLink(wdProc, "eventSeries", "series",  "https://scholia.toolforge.org/event-series/", emptyIfNone=True)
                # scholia colocated with link
                delim=""
                for link in [itemLink,dblpLink,k10PlusLink,scholiaLink,scholiaEventLink,scholiaEventSeriesLink]:
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
    """
    volume search
    """

    def __init__(self,app,volumeInputDiv,volumeDisplay:VolumeDisplay,debug:bool=False):
        """
        constructor

        Args:
            app(App): the justpy bootstrap5 app
            volumeInputDiv(): the input Div
            debug(bool): if True swith debugging on
        """
        self.app=app
        self.debug=debug
        self.app.addMenuLink(text='Endpoint',icon='web',href=self.app.wdSync.endpointConf.website,target="_blank")
        self.volumeInput=self.app.createComboBox(labelText="Volume", a=volumeInputDiv,placeholder='Please type here to search ...',size="120",change=self.onVolumeChange)
        for volume in self.app.wdSync.vm.getList():
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
            if volumeNumber in self.app.wdSync.volumesByNumber:
                volume=self.app.wdSync.volumesByNumber[volumeNumber]
                self.updateVolume(volume)
        except Exception as ex:
            self.app.handleException(ex)


class VolumeListDisplay(Display):
    """
    display all Volumes
    """

    def __init__(self, app, container, debug: bool = False):
        """
        constructor
        Args:
            app:
            container: main container of the content
            debug: If True plot debug messages
        """
        self.app = app
        self.debug = debug
        self.dryRun = True
        self.ignoreErrors = False
        self.container = jp.Div(classes="container", a=container)
        self.rowA = jp.Div(classes="row", a=self.container)
        self.colA1 = jp.Div(classes="col-2", a=self.rowA)
        self.colA2 = jp.Div(classes="col-2", a=self.rowA)
        self.colA3 = jp.Div(classes="col-8", a=self.rowA)
        self.rowB = jp.Div(classes="row", a=self.container)
        self.colB1 = jp.Div(classes="col-12", a=self.rowB)
        self.dryRunButton = Switch(a=self.colA1, labelText="dry run", checked=self.dryRun, disable=True)
        self.dryRunButton.on("input", self.onChangeDryRun)
        self.ignoreErrorsButton = Switch(a=self.colA2, labelText="ignore errors", checked=self.ignoreErrors)
        self.ignoreErrorsButton.on("input", self.onChangeIgnoreErrors)
        self.addFitSizeButton(a=self.colA3)
        self.app.wp.on("page_ready", self.onSizeColumnsToFit)

        try:

            lod=[]
            volumeList=self.app.wdSync.vm.getList()
            reverseVolumeList=sorted(volumeList, key=lambda volume:volume.number, reverse=True)
            for volume in reverseVolumeList:
                validMark = "✅" if volume.valid else "❌"
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
            self.agGrid = jp.AgGrid(a=self.colB1)
            self.agGrid.load_lod(lod)
            self.setDefaultColDef(self.agGrid)
            self.agGrid.options.columnDefs[0].checkboxSelection = True
            self.agGrid.html_columns = [0, 1, 2]
            self.agGrid.on('rowSelected', self.onRowSelected)
        except Exception as ex:
            self.app.handleException(ex)

    def onChangeDryRun(self, msg: dict):
        """
        handle change of DryRun setting

        Args:
            msg(Dict): the justpy event message
        """
        self.dryRun = msg.checked

    async def onChangeIgnoreErrors(self,msg:dict):
        '''
        handle change of IgnoreErrors setting
        
        Args:
            msg(dict): the justpy message
        '''
        self.ignoreErrors=msg.checked

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
                if volumeId is not None and volumeId in self.app.wdSync.volumesByNumber:
                    volume: Volume = self.app.wdSync.volumesByNumber.get(volumeId)
                    proceedingsWikidataId = await self.createProceedingsItemFromVolume(volume, msg)
                    if proceedingsWikidataId is not None:
                        await self.createEventItemAndLinkProceedings(volume,proceedingsWikidataId, msg)
                    else:
                        Alert(a=self.colA3, text=f"Event not created → Error during creation of proceedings item")
                else:
                    Alert(a=self.colA3, text=f"Volume for selected row can not be loaded correctly")
            except Exception as ex:
                self.app.handleException(ex)

    async def createProceedingsItemFromVolume(self, volume: Volume, msg):
        """
        Create wikidata item for proceedings of given volume
        """
        write = not self.dryRun
        if write:
            self.app.wdSync.login()
        # check if already in wikidata → use URN
        urn = getattr(volume, "urn")
        wdItems = self.app.wdSync.getProceedingWdItemsByUrn(urn)
        if len(wdItems) > 0:
            # a proceeding exists with the URN
            alert = Alert(a=self.colA1, text=f"{volume} already in Wikidata see ")
            for wdItem in wdItems:
                jp.Br(a=alert)
                qId = wdItem.split("/")[-1]
                jp.Link(a=alert, href=wdItem, text=qId)
            return qId
        else:
            # A proceedings volume for the URN is not known → create wd entry
            wdRecord = self.app.wdSync.getWikidataProceedingsRecord(volume)
            if self.dryRun:
                prettyData = pprint.pformat(msg.data)
                text = f"{prettyData}"
                alert = Alert(a=self.colA3, text=text)
            qId, errors = self.app.wdSync.addProceedingsToWikidata(wdRecord, write=write, ignoreErrors=self.ignoreErrors)
            if qId is not None:
                alert = Alert(a=self.colA3, text=f"Proceedings entry for {volume} was created!")
                jp.Br(a=alert)
                href = self.app.wdSync.itemUrl(qId)
                jp.Link(a=alert, href=href, text=qId)
            else:
                alert = Alert(a=self.colA3,
                              text=f"An error occured during the creation of the proceedings entry for {volume}")
                jp.Br(a=alert)
                jp.P(a=alert, text=errors)
            return qId

    async def createEventItemAndLinkProceedings(self, volume: Volume, proceedingsWikidataId:str=None, _msg=None):
        """
        Create event  wikidata item for given volume and link 
        the proceedings with the event
        
        Args:
            volume(Volume): the volume for which to create the event item
            proceedingsWikidataId: wikidata id of the proceedings
        """
        try:
            write = not self.dryRun
            if write:
                self.app.wdSync.login()
            proceedingsQId, eventQId, msg = self.app.wdSync.doCreateEventItemAndLinkProceedings(
                    volume,
                    proceedingsWikidataId,
                    write=write)
            if write:
                self.app.wdSync.logout()
            alert = Alert(a=self.colA3, text=msg)
            if proceedingsQId is not None:
                jp.Br(a=alert)
                jp.Link(a=alert,
                        href=f"https://www.wikidata.org/entity/{proceedingsQId}",
                        text=f"Proceedings: {proceedingsQId}")
            if eventQId is not None:
                jp.Br(a=alert)
                jp.Link(a=alert,
                        href=f"https://www.wikidata.org/entity/{eventQId}",
                        text=f"Event: {eventQId}")
        except Exception as ex:
            self.app.handleException(ex)


class WikidataDisplay(Display):
    """
    display wiki data query results
    """

    def __init__(self, app, debug: bool = False):
        """
        constructor
        """
        self.app=app
        self.debug=debug
        self.agGrid=None
        self.app.addMenuLink(text='Endpoint',icon='web',href=self.app.wdSync.endpointConf.website,target="_blank")
        self.pdQueryDisplay=self.createQueryDisplay("Proceedings", self.app.rowA)
        self.readProceedingsButton = jp.Button(
                text="from cache",
                classes="btn btn-primary",
                a=self.app.colA1,
                click=self.onReadProceedingsClick
        )
        self.wikidataRefreshButton = jp.Button(
                text="refresh wikidata",
                classes="btn btn-primary",
                a=self.app.colA1,
                click=self.onWikidataRefreshButtonClick
        )
        self.addFitSizeButton(a=self.app.colA1)
        self.app.wp.on("page_ready", self.onSizeColumnsToFit)

    def createQueryDisplay(self, name: str, a: jp.Component) -> QueryDisplay:
        """
        Args:
            name(str): the name of the query
            a(jp.Component): the ancestor

        Returns:
            QueryDisplay: the created QueryDisplay
        """
        filenameprefix = f"{name}"
        qd = QueryDisplay(
                app=self.app,
                name=name,
                a=a,
                filenameprefix=filenameprefix,
                text=name,
                sparql=self.app.wdSync.sparql,
                endpointConf=self.app.wdSync.endpointConf
        )
        return qd

    async def onReadProceedingsClick(self, _msg):
        """
        read Proceedings button has been clicked
        """
        try:
            proceedingsRecords = self.app.wdSync.loadProceedingsFromCache()
            self.app.showFeedback(f"found {len(proceedingsRecords)} cached wikidata proceedings records")
            self.reloadAgGrid(proceedingsRecords)
            await self.app.wp.update()
            await self.onSizeColumnsToFit(_msg)
        except Exception as ex:
            self.app.handleException(ex)

    async def onWikidataRefreshButtonClick(self,_msg):
        """
        wikidata Refresh button has been clicked
        """
        try:
            _alert = Alert(a=self.app.colA1, text="running SPARQL query to retrieve CEUR-WS proceedings from Wikidata ...")
            await self.app.wp.update()
            self.updateWikidata()
            await self.app.wp.update()
            await self.onSizeColumnsToFit(_msg)
        except Exception as ex:
            self.app.handleException(ex)

    def updateWikidata(self):
        """
        update Wikidata
        """
        self.pdQueryDisplay.showSyntaxHighlightedQuery(self.app.wdSync.wdQuery)
        wdRecords = self.app.wdSync.update()
        _alert = Alert(a=self.app.colA1, text=f"found {len(wdRecords)} wikidata CEUR-WS proceedings records")
        self.reloadAgGrid(wdRecords)
        pass

    def createItemLink(self, row: dict, key: str, separator: str = None) -> str:
        """
        create an item link
        Args:
            row: row object with the data
            key: key of the value for which the link is created
            separator: If not None split the value on the separator and create multiple links
        """
        value = self.getRowValue(row, key)
        if value == Display.noneValue:
            return value
        item = row[key]
        itemLabel = row[f"{key}Label"]
        itemLink = ""
        if separator is not None:
            item_parts = item.split(separator)
            itemLabel_parts = itemLabel.split(separator)
            links = []
            for url, label in zip(item_parts, itemLabel_parts):
                link = self.createLink(url, label)
                links.append(link)
            itemLink = "<br>".join(links)
        else:
            itemLink = self.createLink(item, itemLabel)
        return itemLink

    def reloadAgGrid(self, olod: list, showLimit: int = 10):
        """
        reload the given grid
        """
        if self.debug:
            pprint.pprint(olod[:showLimit])
        if self.agGrid is None:
            self.agGrid = jp.AgGrid(a=self.app.rowB)
        reverseLod = sorted(
                olod,
                key=lambda row: int(row["sVolume"]) if "sVolume" in row else int(row["Volume"]),
                reverse=True
        )
        lod = []
        for row in reverseLod:
            volume = self.getRowValue(row, "sVolume")
            if volume == "?":
                volume = self.getRowValue(row, "Volume")
            volNumber = "?"
            if volume != "?":
                volNumber = int(volume)
                volumeLink = self.createLink(f"http://ceur-ws.org/Vol-{volume}", f"Vol-{volNumber:04}")
            else:
                volumeLink = "?"
            itemLink = self.createItemLink(row, "item")
            eventLink = self.createItemLink(row, "event", separator="|")
            eventSeriesLink = self.createItemLink(row, "eventSeries", separator="|")
            dblpLink = self.createExternalLink(row, "dblpProceedingsId", "dblp", DblpEndpoint.DBLP_REC_PREFIX)
            k10PlusLink = self.createExternalLink(row, "ppnId", "k10plus", "https://opac.k10plus.de/DB=2.299/PPNSET?PPN=")
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

    def __init__(self,version,args=None):
        '''
        Constructor
        
        Args:
            version(Version): the version info for the app
            args(Args): command line arguments
        '''
        self.args=args
        App.__init__(self, version,title="CEUR-WS Volume Browser")
        self.addMenuLink(text='Home',icon='home', href="/")
        self.addMenuLink(text='Volumes',icon='table-large',href="/volumes")
        self.addMenuLink(text='Wikidata Sync',icon='refresh-circle',href="/wikidatasync")
        self.addMenuLink(text='Settings',icon='cog',href="/settings")
        self.addMenuLink(text='github',icon='github', href="https://github.com/WolfgangFahl/pyCEURmake",target="_blank")
        self.addMenuLink(text='Documentation',icon='file-document',href="https://ceur-ws.bitplan.com/index.php/Volume_Browser",target="_blank")
        self.addMenuLink(text='Source',icon='file-code',href="https://github.com/WolfgangFahl/pyCEURmake/blob/main/ceurws/volumebrowser.py",target="_blank")
        self.addMenuLink(text='About',icon='information',href="/about")
        
        # Routes
        jp.app.add_jproute('/settings',self.settings)
        jp.app.add_jproute('/volumes',self.volumes)
        jp.app.add_jproute('/volume/{volnumber}',self.volumePage)
        jp.app.add_jproute('/wikidatasync',self.wikidatasync)
        jp.app.add_jproute('/about',self.about)
        self.templateEnv=TemplateEnv()
        self.wdSync=None
        
        @jp.app.get("/volumes.json")
        async def volumes():
            """
            direct fastapi return of volumes
            """
            if self.wdSync is None:
                self.wdSync=WikidataSync(debug=self.debug)
            volumeList=self.wdSync.vm.getList()
            return volumeList
        
        @jp.app.get("/proceedings.json")
        async def proceedings():
            """
            direct fastapi return of proceedings
            """
            if self.wdSync is None:
                self.wdSync=WikidataSync(debug=self.debug)
            proceedingsList=self.wdSync.loadProceedingsFromCache()
            return proceedingsList
        
        @jp.app.get("/papers.json")
        async def papers():
            """
            direct fastapi return of volumes
            """
            if self.wdSync is None:
                self.wdSync=WikidataSync(debug=self.debug)
            paperList=self.wdSync.pm.getList()
            return paperList

    def setupPage(self,header=""):
        header="""<link rel="stylesheet" href="/static/css/md_style_indigo.css">
<link rel="stylesheet" href="/static/css/pygments.css">
"""+header
        self.wp=self.getWp(header)
        self.wdSync=WikidataSync(debug=self.debug)

    def setupRowsAndCols(self,header=""):
        """
        set up my rows and colors
        """
        self.setupPage(header)
        self.rowA=jp.Div(classes="row",a=self.contentbox)
        self.rowB=jp.Div(classes="row",a=self.contentbox)
        self.rowC=jp.Div(classes="row min-vh-100 vh-100",a=self.contentbox)
        self.rowD=jp.Div(classes="row",a=self.contentbox)
        self.rowE=jp.Div(classes="row",a=self.contentbox)

        self.colA1=jp.Div(classes="col-12",a=self.rowA)
        self.colB1=jp.Div(classes="col-12",a=self.rowB)
        self.colC1=jp.Div(classes="col-12",a=self.rowC)
        self.colD1=jp.Div(classes="col-12",a=self.rowD)
        self.colE1=jp.Div(classes="col-12",a=self.rowE)

        self.feedback=jp.Div(a=self.colD1)
        self.errors=jp.Span(a=self.colE1,style='color:red')

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
        self.volumeListRefresh=VolumeListRefresh(self,a=self.rowA)
        return self.wp

    async def volumePage(self,request):
        '''
        show a page for the given volume
        '''
        app=self
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
        self.volumeDisplay = VolumeDisplay(
                self,
                volumeToolbar=volumeToolbar,
                volumeHeaderDiv=volumeHeaderDiv,
                volumeDiv=volumeDiv
        )
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
            Alert(a=self.colA1,text=f"Volume display for {volnumberStr} failed")
        return self.wp

    async def volumes(self):
        '''
        show the volumes table
        '''
        self.setupRowsAndCols()
        self.volumeListDisplay=VolumeListDisplay(self, container=self.rowA,debug=self.debug)
        #await asyncio.sleep(0.1)
        #await self.volumeListDisplay.onSizeColumnsToFit({})
        return self.wp
    
    async def about(self,request)->"jp.WebPage":
        '''
        show about dialog
        
        Returns:
            jp.WebPage: a justpy webpage renderer
        '''
        self.setupRowsAndCols()
        self.aboutDiv=About(a=self.colB1,version=self.version)
        # get uvicorn root path
        root_path=request.scope.get("root_path")
        self.colC1.inner_html=f"root_path='{root_path}'"
        # @TODO Refactor to pyJustpyWidgets
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
        return self.wp
    
    def start(self,host,port,debug):
        """
        start the server
        """
        self.debug=debug
        jp.justpy(self.content,host=host,port=port)

DEBUG = 0
if __name__ == "__main__":
    if DEBUG:
        sys.argv.append("-d")
    app=VolumeBrowser(Version)
    sys.exit(app.mainInstance())