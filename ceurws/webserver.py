import os
import sys

from fb4.app import AppWrap
from fb4.sse_bp import SSE_BluePrint
from fb4.widgets import Widget, Link, LodTable
from flask import render_template, redirect, url_for, send_from_directory
from lodstorage.lod import LOD

from ceurws.ceur_ws import VolumeManager


class WebServer(AppWrap):
    """
    RESTful api to access and modify OPENRESAECH data
    """

    def __init__(self, host='0.0.0.0', port=5885, verbose=True, debug=False):
        '''
        constructor

        Args:
            host(str): flask host
            port(int): the port to use for http connections
            debug(bool): True if debugging should be switched on
            verbose(bool): True if verbose logging should be switched on
        '''
        self.debug = debug
        self.verbose = verbose
        scriptdir = os.path.dirname(os.path.abspath(__file__))
        template_folder = scriptdir + '/resources/templates'
        super().__init__(host=host, port=port, debug=debug, template_folder=template_folder)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.app_context().push()
        self.authenticate=False
        self.sseBluePrint = SSE_BluePrint(self.app, 'sse')
        self.initCeurwsDatasource()

        @self.app.route('/')
        def home():
            return redirect(url_for('series'))

        @self.app.route('/ceur-ws.css')
        def ceur_ws_css():
            return send_from_directory(f'{os.path.dirname(os.path.abspath(__file__))}/resources/css', "ceur-ws.css")

        @self.app.route('/ceur-ws-semantic.css')
        def ceur_ws_semantic_css():
            return send_from_directory(f'{os.path.dirname(os.path.abspath(__file__))}resources/css', 'ceur-ws-semantic.css')

        @self.app.route('/volumes', methods=['GET'])
        def series():
            valueMap={
                "homepage": lambda value: Link(url=value, title=value),
                "archive": lambda volume: Link(url=f"http://sunsite.informatik.rwth-aachen.de/ftp/pub/publications/CEUR-WS/Vol-{volume.get('number')}.zip", title=f"Vol-{volume.get('number')}.zip"),
                "urn": lambda value: Link(url=f"https://nbn-resolving.org/{value}", title=value),
            }
            values=[v.__dict__.copy() for v in self.ceurws.getList()]
            for volume in values:
                for key, function in valueMap.items():
                    if key in volume:
                        volume[key]=function(volume[key])
                    else:
                        volume[key]=function(volume)
            headers = {v:v for v in LOD.getFields(values)}
            volumes=LodTable(values, headers=headers, name="Volumes", isDatatable=True)
            return render_template('volumes.html', volumes=volumes)


    def initCeurwsDatasource(self):
        """
        Load Ceurws datasource from ConferenceCorpus
        """
        self.ceurws=VolumeManager()
        self.ceurws.loadFromBackup()
        pass



DEBUG = False

def main(argv=None):
    '''main program.'''
    # construct the web application
    web=WebServer()
    home= os.path.expanduser("~")
    parser = web.getParser(description="ceurws")
    parser.add_argument('-t', '--target', default="wikirenderTest", help="wikiId of the target wiki [default: %(default)s]")
    parser.add_argument('--verbose', default=True, action="store_true", help="should relevant server actions be logged [default: %(default)s]")
    args = parser.parse_args()
    web.optionalDebug(args)
    #web.init(wikiId=args.target,wikiTextPath=args.wikiTextPath)
    web.run(args)

if __name__ == '__main__':
    sys.exit(main())