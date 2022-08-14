'''
Created on 2022-08-14

@author: wf
'''
import justpy as jp
from jpwidgets.bt5widgets import App, ProgressBar, Spinner, Alert
from ceurws.ceur_ws import VolumeManager, Volume, CEURWS
from lodstorage.lod import LOD
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
        self.vm=VolumeManager()
        self.vm.loadFromIndexHtml(force=True)
        self.volumesByNumber, _duplicates = LOD.getLookup(self.vm.getList(), 'number')
        self.volumeList=self.vm.getList()
        self.volumeCount=len(self.volumeList)
        self.volumeInput=self.app.createComboBox(labelText="Volume", a=a,placeholder='Please type here to search ...',size="120",change=self.onVolumeChange)
        for volume in self.vm.getList():
            for attr in ["desc","h1"]:
                if not hasattr(volume, attr):
                    setattr(volume, attr, "?")
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
            if volumeNumber in self.volumesByNumber:    
                volume=self.volumesByNumber[volumeNumber]
                self.updateVolume(volume)
        except Exception as ex:
            self.app.handleException(ex)
  
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
        self.addMenuLink(text='Settings',icon='cog',href="/settings")
        self.addMenuLink(text='github',icon='github', href="https://github.com/WolfgangFahl/pyCEURmake/issues/16")
        self.addMenuLink(text='Documentation',icon='file-document',href="https://ceur-ws.bitplan.com/index.php/Volume_Browser")
        self.addMenuLink(text='Source',icon='file-code',href="https://github.com/WolfgangFahl/pyCEURmake/blob/main/ceurws/volumebrowser.py")
        # Routes
        jp.Route('/settings',self.settings)
        
        
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
        
    async def settings(self):
        '''
        settings
        '''
        self.setupRowsAndCols()
        return self.wp
    
    async def content(self):
        '''
        show the content
        '''
        self.setupRowsAndCols()
        self.volumeSearch=VolumeSearch(self,self.colA1,self.rowB)
        return self.wp
        
        
DEBUG = 1
if __name__ == "__main__":
    if DEBUG:
        sys.argv.append("-d")
    app=VolumeBrowser(Version)
    sys.exit(app.mainInstance())