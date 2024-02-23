"""
Created on 2024-02-23

@author: wf
"""
from ngwidgets.lod_grid import GridConfig,ListOfDictsGrid
from ngwidgets.widgets import Link
from nicegui import ui

from ceurws.ceur_ws import Volume
from ceurws.view import View
from ceurws.wikidatasync import DblpEndpoint


class VolumeView(View):
    """
    displays a single volume
    """

    def __init__(self, solution, parent):
        """
        constructor

        Args:
            solution: the solution
            parent: the parent UI container

        """
        self.solution = solution
        self.parent = parent
        self.volumeToolBar = None
        self.wdSync = self.solution.wdSync
        self.wdSpan = None

    def setup_ui(self):
        """
        setup my User Interface elements
        """
        with self.parent:
            with ui.row() as self.volumeToolBar:
                self.volumeRefreshButton = (
                    ui.button(
                        icon="refresh",
                        on_click=self.onRefreshButtonClick,
                    )
                    .classes("btn btn-primary btn-sm col-1")
                    .tooltip("Refresh from CEUR-WS Volume page")
                )
                self.wikidataButton = (
                    ui.button(
                        icon="web",
                        on_click=self.onWikidataButtonClick,
                    )
                    .classes("btn btn-primary btn-sm col-1")
                    .tooltip("Export to Wikidata")
                )
            self.header_view = ui.html()
            self.iframe_view = ui.html().classes("w-full").style("height: 80vh;")

    def updateWikidataSpan(self, qId: str, volume: Volume):
        """
        create a Wikidata Export span

        Args:
            a(): ancestor
            qId(str): wikidata item Q Identifier
            volume(Volume): the Volume
        """
        if self.wdSpan is None:
            self.wdSpan = ui.html()
        volume_link = Link.create(
            url=self.volume.url, text=f"{volume}:{volume.acronym}"
        )
        wd_url = self.wdSync.itemUrl(qId)
        wd_link = Link.create(url=wd_url, text=f"{qId} ")
        self.wdSpan.content = f"{volume_link}{wd_link}"

    def showVolume(self, volume):
        """
        show the given volume

        Args:
            volume(Volume): the volume to show
        """
        try:
            self.volume = volume
            if self.volumeToolBar is None:
                self.setup_ui()

            wdProc = self.wdSync.getProceedingsForVolume(volume.number)
            self.wikidataButton.disabled = wdProc is not None
            links = ""
            if wdProc is not None:
                # wikidata proceedings link
                itemLink = self.createLink(wdProc["item"], "wikidataitem")
                # dblp proceedings link
                dblpLink = self.createExternalLink(
                    wdProc,
                    "dblpEventId",
                    "dblp",
                    DblpEndpoint.DBLP_EVENT_PREFIX,
                    emptyIfNone=True,
                )
                # k10plus proceedings link
                k10PlusLink = self.createExternalLink(
                    wdProc,
                    "ppnId",
                    "k10plus",
                    "https://opac.k10plus.de/DB=2.299/PPNSET?PPN=",
                    emptyIfNone=True,
                )
                # scholia proceedings link
                scholiaLink = self.createExternalLink(
                    wdProc,
                    "item",
                    "scholia",
                    "https://scholia.toolforge.org/venue/",
                    emptyIfNone=True,
                )
                # scholia event link
                scholiaEventLink = self.createExternalLink(
                    wdProc,
                    "event",
                    "event",
                    "https://scholia.toolforge.org/event/",
                    emptyIfNone=True,
                )
                # scholia event series link
                scholiaEventSeriesLink = self.createExternalLink(
                    wdProc,
                    "eventSeries",
                    "series",
                    "https://scholia.toolforge.org/event-series/",
                    emptyIfNone=True,
                )
                # scholia colocated with link
                delim = ""
                for link in [
                    itemLink,
                    dblpLink,
                    k10PlusLink,
                    scholiaLink,
                    scholiaEventLink,
                    scholiaEventSeriesLink,
                ]:
                    if link:
                        links += delim + link
                        delim = "&nbsp;"

            # template=self.templateEnv.getTemplate('volume_index_body.html')
            # html=template.render(volume=volume)
            headerHtml = f"""{links}<h3 style='font-size: 24px; font-weight: normal; margin-top: 20px; margin-bottom: 10px;'>{volume.h1}</h3>
    <a href='{volume.url}'>{volume.acronym}<a>
    {volume.title}<br>
    {volume.desc}
    published: {volume.pubDate}
    submitted By: {volume.submittedBy}"""
            iframeHtml = f"""
            <iframe src='{volume.url}' style='width: 100%; height: 80vh; border: none;'></iframe>"""
            self.header_view.content = headerHtml
            self.iframe_view.content = iframeHtml

        except Exception as ex:
            self.solution.handle_exception(ex)

    async def onRefreshButtonClick(self, _args):
        try:
            self.volume.extractValuesFromVolumePage()
            msg = f"updated from {self.volume.url}"
            ui.notify(msg)
            self.showVolume(self.volume)
            # self.wdSync.storeVolumes()
        except Exception as ex:
            self.solution.handle_exception(ex)

    async def onWikidataButtonClick(self, _args):
        """
        handle wikidata sync request
        """
        try:
            wdRecord = self.wdSync.getWikidataProceedingsRecord(self.volume)
            qId, err = self.wdSync.addProceedingsToWikidata(
                wdRecord, write=True, ignoreErrors=False
            )
            if qId is not None:
                msg = f"wikidata export of {self.volume.volumeNumber} to {qId} done"
                ui.notify(msg)
                self.updateWikidataSpan(
                    wdSync=self.app.wdSync, qId=qId, volume=self.volume
                )
            else:
                err_msg = f"error:{err}"
                self.solution.log_view.push(err_msg)
        except Exception as ex:
            self.solution.handle_exception(ex)
            
class VolumeListView(View):
    """
    show a list of volumes a table
    """
    
    def __init__(self, solution, parent):
        """
        constructor

        Args:
            solution: the solution
            parent: the parent UI container

        """
        self.solution = solution
        self.parent = parent
        self.wdSync=self.solution.wdSync
        self.get_volume_lod()
        self.setup_ui()
        
    def setup_ui(self):
        """
        show my volumes as a list
        """
        try:
            with ui.row() as self.button_row:
                self.wikidataButton = (
                    ui.button(
                        icon="web",
                        on_click=self.onWikidataButtonClick,
                    )
                    .classes("btn btn-primary btn-sm col-1")
                    .tooltip("Export to Wikidata")
                )
                pass
            with ui.row() as self.grid_row:    
                grid_config = GridConfig(
                    key_col="Vol",
                    multiselect=True)
                self.lod_grid=ListOfDictsGrid(lod=self.lod,config=grid_config)
                # Modify the columnDefs for the "Title" column after grid initialization
                for col_def in self.lod_grid.ag_grid.options["columnDefs"]:
                    if col_def["field"] == "Title":  # Identify the "Title" column
                        col_def["maxWidth"] = 400  # width in pixels
                self.lod_grid.sizeColumnsToFit()
        except Exception as ex:
            self.handle_exception(ex)
            
    async def onWikidataButtonClick(self, _args):
        """
        handle wikidata sync request
        """
        try:
            selected_rows = await self.lod_grid.get_selected_rows()
            for row in selected_rows:
                vol_number=row["#"]
                volume = self.wdSync.volumesByNumber[vol_number]
                ui.notify(f"exporting {vol_number}")
            pass
        except Exception as ex:
            self.handle_exception(ex)
        
    def get_volume_lod(self):
        """
        get the list of dict of all volumes
        """
        self.lod = []
        volumeList = self.wdSync.vm.getList()
        reverseVolumeList = sorted(
            volumeList, key=lambda volume: volume.number, reverse=True
        )
        for volume in reverseVolumeList:
            validMark = "✅" if volume.valid else "❌"
            self.lod.append(
                {
                    "#": volume.number,
                    "Vol": self.createLink(volume.url, f"Vol-{volume.number:04}"),
                    "Acronym": self.getValue(volume, "acronym"),
                    "Title": self.getValue(volume, "title"),
                    "Loctime": self.getValue(volume, "loctime"),
                    "Published": self.getValue(volume, "published"),
                    "SubmittedBy": self.getValue(volume, "submittedBy"),
                    "valid": validMark,
                }
            )
