"""
Created on 2024-02-22

@author: wf
"""
from ngwidgets.input_webserver import InputWebserver, InputWebSolution
from ngwidgets.webserver import WebserverConfig
from nicegui import Client, ui, app
from nicegui.events import ValueChangeEventArguments

from ceurws.volume_view import VolumeView
from ceurws.version import Version
from ceurws.wikidatasync import WikidataSync
import os
from pathlib import Path

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
        
        @app.get("/volumes.json")
        async def volumes():
            """
            direct fastapi return of volumes
            """
            volumeList = self.wdSync.vm.getList()
            return volumeList

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
        self.wdSync=self.webserver.wdSync
        self.get_volume_options()

    def get_volume_options(self):
        """
        get the volume options
        """
        # Initialize an empty dictionary to store volume number as key and title as value
        self.volume_options = {}
        self.volumes_by_number = {}

        # Populate the dictionary with volume numbers and titles
        for volume in self.wdSync.vm.getList():
            self.volumes_by_number[volume.number] = volume

        reverse_keys = sorted(self.volumes_by_number.keys(), reverse=True)
        for volume_number in reverse_keys:
            volume = self.volumes_by_number[volume_number]
            self.volume_options[volume.number] = f"Vol-{volume.number}:{volume.title}"
        pass
    
    def prepare_ui(self):
        """
        prepare the user interface
        """
        InputWebSolution.prepare_ui(self)
        # does not work as expected ...
        #self.add_css()
        
    def add_css(self):
        # Get the correct path to the 'css' directory
        css_directory_path = Path(__file__).parent.parent / "css"
        # Check if the directory exists before trying to serve it
        if css_directory_path.is_dir():
            # Serve files from the 'css' directory at the '/css' route
            app.add_static_files('/css', str(css_directory_path))
        
            # Iterate over all .css files in the directory
            for css_file in os.listdir(css_directory_path):
                if css_file.endswith(".css"):
                    # Add the link tag for the css file to the head of the HTML document
                    ui.add_head_html(f'<link rel="stylesheet" type="text/css" href="/css/{css_file}">')


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
                            selection=self.volume_options,
                            with_input=True,
                            on_change=self.volume_selected,
                        )
                    self.volume_view=VolumeView(self,self.container)   
            except Exception as ex:
                self.handle_exception(ex)

        await self.setup_content_div(show)

    async def volume_selected(self, args: ValueChangeEventArguments):
        """
        when a volume is selected show the details in the Volume View
        """
        vol_number = args.value
        volume = self.volumes_by_number[vol_number]
        self.volume_view.showVolume(volume)
        pass
