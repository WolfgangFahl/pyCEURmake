'''
Created on 2024-02-22

@author: wf
'''
from ngwidgets.input_webserver import InputWebserver, InputWebSolution
from ngwidgets.webserver import WebserverConfig
from ceurws.version import Version
from nicegui import Client,ui
from ceurws.wikidatasync import WikidataSync

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
            short_name="spf"
        )
        server_config = WebserverConfig.get(config)
        server_config.solution_class =CeurWsSolution
        return server_config

    def __init__(self):
        """
        constructor
        """
        InputWebserver.__init__(self, config=CeurWsWebServer.get_config())
        
    def configure_run(self):
        InputWebserver.configure_run(self)
        self.wdSync = WikidataSync.from_args(self.args)
        self.volume_options=[]
        for volume in self.wdSync.vm.getList():
            title = f"Vol-{volume.number}:{volume.title}"
            self.volume_options.append(title)
        
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
        
    async def home(self):
        """
        home page selection
        """

        def show():
            try:
                with ui.row():
                    self.volume_select=ui.select(options=self.webserver.volume_options, with_input=True)
            except Exception as ex:
                self.handle_exception(ex)

        await self.setup_content_div(show)