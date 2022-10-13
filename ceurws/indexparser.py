'''
Created on 11.08.2022

@author: wf
'''
import datetime
import html
import re
from ceurws.textparser import Textparser

class IndexHtmlParser(Textparser):
    '''
    CEUR-WS Index.html parser
    '''

    def __init__(self,htmlText,debug:bool):
        '''
        Constructor
        
        Args:
            htmlText(str): the HTML text of the index page
            debug(bool): if TRUE switch debugging on
        '''
        Textparser.__init__(self,debug=debug)
        self.htmlText=htmlText
        # soup (in memory is slow)
        # soup = BeautifulSoup(html_page, 'html.parser'
        self.lines=htmlText.split("\n")
        #trStart, trEnd = makeHTMLTags("tr")
        #self.tr = trStart + SkipTo(trEnd).setResultsName("tr") + trEnd.suppress()
        self.linkPattern=re.compile(r'''.*href=[\'"]?([^\'" >]+).*''',re.I)
        self.volPattern=re.compile("http://ceur-ws.org/Vol-([0-9]+)")
        self.volLinkPattern=re.compile(r'''.*<a\s+href=[\'"]http://ceur-ws.org/Vol-([0-9]+)[/]?[\'"]>([^<]*)</a>.*''',re.I | re.DOTALL)
        
    def find(self,startLine:int,needleRegex:str,step:int=1)->int:
        '''
        find the next line with the given regular expression
        
        Args:
            startLine(int): index of the line to start search
            needleRegex(str): the regular expression to search for
            step(int): the steps to take e.g. +1 for forward -1 for backwards
            
        Return:
            int: the line number of the line or None if nothing was found
        '''
        pattern=re.compile(needleRegex,re.I)
        lineNo=startLine
        while lineNo>=1 and lineNo<len(self.lines)+1:
            line=self.lines[lineNo-1]
            if pattern.match(line):
                return lineNo
            lineNo+=step
        return None
    
    def findVolume(self,startLine:int,expectedTr:int=3)->int:
        '''
        find Volume lines from the given startLine
        
        Args:
            startLine(int): index of the line to search
        
        Returns:
            endLine of the volume html or None
        '''
        trStartLine=self.find(startLine, "<tr><th")
        if trStartLine is not None:
            lineNo=trStartLine+1
            trCount=1
            while lineNo<len(self.lines):
                trLine=self.find(lineNo, "<tr>")
                if trLine is None:
                    break
                else:
                    lineNo=trLine+1
                    trCount+=1
                    if trCount==expectedTr:
                        trEndLine=self.find(lineNo+1,"</tr>")
                        return trStartLine,trEndLine
        return None,None 
    
    def setVolumeNumber(self,volume,href):
        '''
        set the volumen number
        '''
        if href is None:
            return
        volNumber=self.getMatch(self.volPattern, href, 1)
        if volNumber is not None:
            volume["number"]=int(volNumber)
            
    def setVolumeName(self,volume,line):
        '''
        set the volume name
        '''
        volName=self.getMatch(self.volLinkPattern, line, 2)
        if volName is not None:
            valid=True
            if not volName.startswith("http:"):
                invalidKeys=["deleted upon editor request","Not used"]
                for invalidKey in invalidKeys:
                    if invalidKey in volName:
                        href=self.getMatch(self.linkPattern, line, 1)
                        self.setVolumeNumber(volume, href)
                        valid=False
                volume["valid"]=valid
                if valid:
                    volName=html.unescape(volName)
                    volName=Textparser.sanitize(volName)
                    volume["volname"]=volName
                
    def setVolumeTitle(self,volume:dict,lineIndex:int):
        '''
        set the volume title
        
        Args:
            volume(dict): the volumeRecord to modify
            lineIndex: where to start setting the volumeTitle
        '''
        editedByLine=self.find(lineIndex, "Edited by:")
        if editedByLine is not None:
            tdLine=self.find(editedByLine,"<td bgcolor",step=-1)
            if tdLine is not None:
                tdIndex=tdLine-1
                title=""
                delim=""
                while tdIndex < len(self.lines):
                    line=self.lines[tdIndex]
                    if line.startswith("Edited by:"):
                        break
                    for tag in ['<TD bgcolor="#FFFFFF">&nbsp;</TD><TD bgcolor="#FFFFFF">','<TD bgcolor="#FFFFFF">', '<td bgcolor="#FFFFFF">',"<BR>","<br>"]:
                        line=line.replace(tag,"")
                    line=line.replace("\r"," ")
                    title+=line+delim
                    delim=" "
                    tdIndex+=1
                volume["tdtitle"]=html.unescape(title).strip()

    def getInfo(self,volume:dict,info:str,pattern,line:str):
        '''
        get the info info for the given patterns trying to match the pattern on
        the given line
        
        Args:
            volume(dict): the result dict
            info(str): the name of the dict key to fill
            pattern(regexp): the regular expression to check
            line(str): the line to check
        '''
        infoValue=self.getMatch(pattern, line, 1)
        if infoValue is not None:
            for delim in ["<BR>","<br>"]:
                infoValue=infoValue.replace(delim,"")
            infoValue=infoValue.strip()
            if info in ["editors","submittedBy"]:
                infoValue=html.unescape(infoValue)
            if info=="pubDate":
                try:
                    infoValue=datetime.datetime.strptime(infoValue, '%d-%b-%Y')
                    published=infoValue.strftime("%Y-%m-%d")
                    volume["published"]=published
                    volume["year"]=infoValue.year
                except ValueError as ve:
                    msg=f"pubDate: {infoValue} of {volume} parsing failed with {ve}"
                    self.log(msg)
            if info in ["urn","url","archive"]:
                href=self.getMatch(self.linkPattern, infoValue, 1)
                if href is not None:
                    infoValue=href
                    if info=="url":
                        self.setVolumeNumber(volume,href)
                    if info=="urn":
                        infoValue=href.replace("https://nbn-resolving.org/","")
            volume[info]=infoValue
    
    def parseVolume(self,volCount:int,fromLine:int,toLine:int,verbose:bool):
        '''
        parse a volume from the given line range
        '''
        lineCount=toLine-fromLine
        volume={}
        volume["fromLine"]=fromLine
        volume["toLine"]=toLine
        volume["valid"]=False
        volume["url"]=None
        volume["acronym"]=None
        volume["title"]=None
        volume["loctime"]=None
        self.setVolumeTitle(volume, fromLine)
        
        infoPattern={}
        infoMappings = [
            ("URN","urn"),
            ("ONLINE","url"),
            ("ARCHIVE","archive"),
            ("Edited by","editors"),
            ("Submitted by","submittedBy"),
            ("Published on CEUR-WS","pubDate")]
        for prefix, info in infoMappings:
            infoPattern[info]=re.compile(f"^\s*{prefix}:(.*)")
        for lineIndex in range(fromLine,toLine):
            line=self.lines[lineIndex]
            for info,pattern in infoPattern.items():
                self.getInfo(volume,info,pattern,line)
            self.setVolumeName(volume,line)
            if verbose:
                print(line)        
        volumeNumber=volume.get('number','?')
        acronym=volume.get('acronym','?')
        self.log(f"{volumeNumber:4}-{volCount:4}:{fromLine}+{lineCount} {acronym}")
        return volume
        
    def parse(self,limit:int=1000000,verbose:bool=False):
        '''
        parse my html code for Volume info
        '''
        lineNo=self.find(1, '<TABLE id="MAINTABLE"')
        volCount=0
        volumes={}
        while lineNo<len(self.lines):
            expectedTr=3
            volStartLine,volEndLine=self.findVolume(lineNo,expectedTr=expectedTr)
            if volStartLine is None or volCount>=limit:
                break
            else:
                volCount+=1
                volume=self.parseVolume(volCount,volStartLine, volEndLine,verbose=verbose)
                # synchronize on <tr><th and not on end since trailing TR might be missing
                lineNo=volStartLine+1
                if "number" in volume:
                    volumes[volume["number"]]=volume
                else:
                    self.log(f"volume not found for volume at {volStartLine}")
        return volumes