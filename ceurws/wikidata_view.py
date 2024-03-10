'''
Created on 2024-02-23

@author: wf
'''
from ceurws.view import View
from ceurws.wikidatasync import DblpEndpoint
from ngwidgets.lod_grid import ListOfDictsGrid
from nicegui import ui
from typing import Dict,List
from wd.query_view import QueryView

class WikidataView(View):
    """
    Wikidata View
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
        self.setup_ui()
        
    async def update_proceedings(self):
        """
        update the cached proceedings
        """
        try:
            self.proceedings_records=self.solution.wdSync.loadProceedingsFromCache()
            with self.parent:
                ui.notify(f"found {len(self.proceedings_records)} cached wikidata proceedings records")
                self.reload_aggrid(self.proceedings_records)
        except Exception as ex:
            self.solution.handle_exception(ex)
            
    def reload_aggrid(self,olod:List):
        """
        reload my aggrid with the list of Volumes
        """
        reverseLod = sorted(
            olod,
            key=lambda row: int(row.get("sVolume") or row.get("Volume") or 0),
            reverse=True,
        )
        lod = []
        for row in reverseLod:
            volume = self.getRowValue(row, "sVolume")
            if volume == "?":
                volume = self.getRowValue(row, "Volume")
            volNumber = "?"
            if volume != "?":
                volNumber = int(volume)
                volumeLink = self.createLink(
                    f"http://ceur-ws.org/Vol-{volume}", f"Vol-{volNumber:04}"
                )
            else:
                volumeLink = "?"
            itemLink = self.createItemLink(row, "item")
            eventLink = self.createItemLink(row, "event", separator="|")
            eventSeriesLink = self.createItemLink(row, "eventSeries", separator="|")
            dblpLink = self.createExternalLink(
                row, "dblpProceedingsId", "dblp", DblpEndpoint.DBLP_REC_PREFIX
            )
            k10PlusLink = self.createExternalLink(
                row, "ppnId", "k10plus", "https://opac.k10plus.de/DB=2.299/PPNSET?PPN="
            )
            lod.append(
                {
                    "#": volume,
                    "item": itemLink,
                    "volume": volumeLink,
                    "acronym": self.getRowValue(row, "short_name"),
                    "dblp": dblpLink,
                    "k10plus": k10PlusLink,
                    "event": eventLink,
                    "series": eventSeriesLink,
                    "ordinal": self.getRowValue(row, "eventSeriesOrdinal"),
                    # "title":row.get("title","?"),
                }
            )
        self.lod_grid.load_lod(lod)
        self.lod_grid.sizeColumnsToFit()
        
    async def on_refresh_button_click(self):
        """
        handle the refreshing of the proceedings from wikidata
        """
        try:
            ui.notify("wikidata refresh button clicked")
            wd_records=self.solution.wdSync.update()
            self.lod_grid.load_lod(wd_records)
            pass
        except Exception as ex:
            self.solution.handle_exception(ex)
        
    def setup_ui(self):
        """
        setup my User Interface elements
        """
        with self.parent:
            with ui.row() as self.tool_bar:
                self.refresh_button = (
                    ui.button(
                        icon="refresh",
                        on_click=self.on_refresh_button_click,
                    )
                    .classes("btn btn-primary btn-sm col-1")
                    .tooltip("Refresh from Wikidata SPARQL endpoint")
                )
                self.query_view=QueryView(self.solution,
                    name="CEUR-WS wikidata sync",
                    sparql_endpoint=self.solution.wdSync.wikidata_endpoint)
                self.query_view.show_query(self.solution.wdSync.wdQuery.query)
            
            #grid_config = GridConfig(
            #        key_col="Vol",
            #        multiselect=True)
            
            self.lod_grid=ListOfDictsGrid()
            ui.timer(0,self.update_proceedings,once=True)
            pass
    
