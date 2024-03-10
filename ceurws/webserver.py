"""
Created on 2024-02-22

@author: wf
"""
import os
from pathlib import Path
from typing import List

from fastapi import HTTPException
from fastapi.responses import ORJSONResponse
from ngwidgets.input_webserver import InputWebserver, InputWebSolution
from ngwidgets.webserver import WebserverConfig
from nicegui import Client, app, ui
from nicegui.events import ValueChangeEventArguments

from ceurws.models.dblp import DblpPaper, DblpProceeding, DblpScholar
from ceurws.version import Version
from ceurws.volume_view import VolumeView, VolumeListView
from ceurws.wikidatasync import WikidataSync
from ceurws.wikidata_view import WikidataView
from lodstorage.query  import EndpointManager

class CeurWsWebServer(InputWebserver):
    """
    webserver
    """

    @classmethod
    def get_config(cls) -> WebserverConfig:
        copy_right = "(c)2023-2024 Wolfgang Fahl"
        config = WebserverConfig(
            copy_right=copy_right,
            version=Version(),
            default_port=9998,
            timeout=10.0,
            short_name="spf",
        )
        server_config = WebserverConfig.get(config)
        server_config.solution_class = CeurWsSolution
        return server_config

    def __init__(self):
        """
        constructor
        """
        InputWebserver.__init__(self, config=CeurWsWebServer.get_config())
       
        @ui.page("/volumes")
        async def show_volumes(client: Client):
            return await self.page(
                client,CeurWsSolution.volumes
            )
            
        @ui.page("/volume/{volnumber}")
        async def show_volume_page(client: Client,vol_number):
            return await self.page(
                client,CeurWsSolution.volumePage,vol_number
            )
            
        @ui.page("/wikidatasync")
        async def wikidatasync(client: Client):
            return await self.page(
                client,CeurWsSolution.wikidatasync
            )
     
        @app.get("/volumes.json")
        async def volumes():
            """
            direct fastapi return of volumes
            """
            volumeList = self.wdSync.vm.getList()
            return volumeList

        @app.get("/proceedings.json")
        async def proceedings():
            """
            direct fastapi return of proceedings
            """
            proceedingsList = self.wdSync.loadProceedingsFromCache()
            return ORJSONResponse(proceedingsList)

        @app.get("/papers.json")
        async def papers():
            """
            direct fastapi return of papers
            """
            paperList = self.wdSync.pm.getList()
            return paperList

        @app.get(
            "/papers_dblp.json",
            tags=["dblp complete dataset"],
            # response_model= List[DblpPaper]
        )
        async def papers_dblp():
            """
            direct fastapi return of paper information from dblp
            """
            papers = self.wdSync.dblpEndpoint.get_all_ceur_papers()
            return ORJSONResponse(papers)

        @app.get(
            "/authors_dblp.json",
            tags=["dblp complete dataset"],
            # response_model=List[DblpAuthor]
        )
        async def authors_papers_dblp():
            """
            direct fastapi return of paper information from dblp
            """
            authors = self.wdSync.dblpEndpoint.get_all_ceur_authors()
            return ORJSONResponse(content=authors)

        @app.get("/dblp/papers", tags=["dblp complete dataset"])
        async def dblp_papers(limit: int = 100, offset: int = 0) -> List[DblpPaper]:
            """
            Get ceur-ws volumes form dblp
            Args:
                limit: max number of returned papers
                offset:

            Returns:
            """
            papers = self.wdSync.dblpEndpoint.get_all_ceur_papers()
            return papers[offset:limit]

        @app.get("/dblp/editors", tags=["dblp complete dataset"])
        async def dblp_editors(limit: int = 100, offset: int = 0) -> List[DblpScholar]:
            """
            Get ceur-ws volume editors form dblp
            Args:
                limit: max number of returned papers
                offset:

            Returns:
            """
            editors = self.wdSync.dblpEndpoint.get_all_ceur_editors()
            return editors[offset:limit]

        @app.get("/dblp/volumes", tags=["dblp complete dataset"])
        async def dblp_volumes(limit: int = 100, offset: int = 0) -> List[DblpPaper]:
            """
            Get ceur-ws volumes form dblp
            Args:
                limit: max number of returned papers
                offset:

            Returns:
            """
            proceedings = self.wdSync.dblpEndpoint.get_all_ceur_proceedings()
            return proceedings[offset:limit]

        @app.get("/dblp/volume/{volume_number}", tags=["dblp"])
        async def dblp_volume(volume_number: int) -> DblpProceeding:
            """
            Get ceur-ws volume form dblp
            """
            try:
                proceeding = self.wdSync.dblpEndpoint.get_ceur_proceeding(volume_number)
            except Exception as e:
                raise HTTPException(status_code=404, detail=e.msg)
            if proceeding:
                return proceeding
            else:
                raise HTTPException(status_code=404, detail="Volume not found")

        @app.get("/dblp/volume/{volume_number}/editor", tags=["dblp"])
        async def dblp_volume_editors(volume_number: int) -> List[DblpScholar]:
            """
            Get ceur-ws volume editors form dblp
            """
            try:
                proceeding = self.wdSync.dblpEndpoint.get_ceur_proceeding(volume_number)
            except Exception as e:
                raise HTTPException(status_code=404, detail=e.msg)
            if proceeding:
                return proceeding.editors
            else:
                raise HTTPException(status_code=404, detail="Volume not found")

        @app.get("/dblp/volume/{volume_number}/paper", tags=["dblp"])
        async def dblp_volume_papers(volume_number: int) -> List[DblpPaper]:
            """
            Get ceur-ws volume papers form dblp
            Args:
                volume_number: number of the volume

            Returns:
            """
            papers = self.wdSync.dblpEndpoint.get_ceur_volume_papers(volume_number)
            return papers

        @app.get("/dblp/volume/{volume_number}/paper/{paper_id}", tags=["dblp"])
        async def dblp_paper(volume_number: int, paper_id: str) -> DblpPaper:
            """
            Get ceur-ws volume paper form dblp
            """
            paper = self.wdSync.dblpEndpoint.get_ceur_volume_papers(volume_number)
            if paper:
                for paper in paper:
                    if paper.pdf_id == f"Vol-{volume_number}/{paper_id}":
                        return paper
                raise HTTPException(status_code=404, detail="Paper not found")
            else:
                raise HTTPException(status_code=404, detail="Volume not found")

        @app.get("/dblp/volume/{volume_number}/paper/{paper_id}/author", tags=["dblp"])
        async def dblp_paper_authors(
            volume_number: int, paper_id: str
        ) -> List[DblpScholar]:
            """
            Get ceur-ws volume paper form dblp
            """
            paper = self.wdSync.dblpEndpoint.get_ceur_volume_papers(volume_number)
            if paper:
                for paper in paper:
                    if paper.pdf_id == f"Vol-{volume_number}/{paper_id}":
                        return paper.authors
                raise HTTPException(status_code=404, detail="Paper not found")
            else:
                raise HTTPException(status_code=404, detail="Volume not found")

    def configure_run(self):
        """
        configure command line specific details
        """
        InputWebserver.configure_run(self)
        self.wdSync = WikidataSync.from_args(self.args)


class CeurWsSolution(InputWebSolution):
    """
    CEUR-WS Volume browser solution

    """

    def __init__(self, webserver: CeurWsWebServer, client: Client):
        """
        Initialize the solution

        Calls the constructor of the base solution
        Args:
            webserver (CeurWsWebServer): The webserver instance associated with this context.
            client (Client): The client instance this context is associated with.
        """
        super().__init__(webserver, client)  # Call to the superclass constructor
        self.wdSync = self.webserver.wdSync
        
    def configure_menu(self):
        InputWebSolution.configure_menu(self)
        self.link_button(
            name="volumes", icon_name="table", target="/volumes"
        )
        self.link_button(
            name="wikidata",icon_name="cloud_sync",target="/wikidatasync"
        )

    def prepare_ui(self):
        """
        prepare the user interface
        """
        InputWebSolution.prepare_ui(self)
        # does not work as expected ...
        # self.add_css()

    def add_css(self):
        # Get the correct path to the 'css' directory
        css_directory_path = Path(__file__).parent.parent / "css"
        # Check if the directory exists before trying to serve it
        if css_directory_path.is_dir():
            # Serve files from the 'css' directory at the '/css' route
            app.add_static_files("/css", str(css_directory_path))

            # Iterate over all .css files in the directory
            for css_file in os.listdir(css_directory_path):
                if css_file.endswith(".css"):
                    # Add the link tag for the css file to the head of the HTML document
                    ui.add_head_html(
                        f'<link rel="stylesheet" type="text/css" href="/css/{css_file}">'
                    )
                    
    async def wikidatasync(self):
        """
        show the wikidata sync table
        """
        def show():
            self.wikidata_view =WikidataView(
                self, self.container
            )
        await self.setup_content_div(show)
        
    async def volumes(self):
        """
        show the volumes table
        """
        def show():
            self.volume_list_view = VolumeListView(
                self, self.container
            )
        await self.setup_content_div(show)

    async def home(self):
        """
        home page selection
        """

        def show():
            try:
                with self.container:
                    with ui.row() as self.select_container:
                        self.volume_select = self.add_select(
                            "Volume",
                            selection=self.wdSync.volumeOptions,
                            with_input=True,
                            on_change=self.volume_selected,
                        ).props("size=120")
                    self.volume_view = VolumeView(self, self.container)
            except Exception as ex:
                self.handle_exception(ex)

        await self.setup_content_div(show)

    async def volume_selected(self, args: ValueChangeEventArguments):
        """
        when a volume is selected show the details in the Volume View
        """
        vol_number = args.value
        volume = self.wdSync.volumesByNumber[vol_number]
        self.volume_view.showVolume(volume)
        pass
