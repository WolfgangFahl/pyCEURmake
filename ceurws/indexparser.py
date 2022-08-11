'''
Created on 11.08.2022

@author: wf
'''
#from pyparsing import makeHTMLTags, SkipTo, htmlComment
import html
import re
# import logging

class IndexHtmlParser():
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
        self.htmlText=htmlText
        self.debug=debug
        # soup (in memory is slow)
        # soup = BeautifulSoup(html_page, 'html.parser'
        self.lines=htmlText.split("\n")
        #trStart, trEnd = makeHTMLTags("tr")
        #self.tr = trStart + SkipTo(trEnd).setResultsName("tr") + trEnd.suppress()
        self.linkPattern=re.compile(r'''.*href=[\'"]?([^\'" >]+).*''',re.I)
        self.volPattern=re.compile("http://ceur-ws.org/Vol-([0-9]+)")
        self.volLinkPattern=re.compile(r'''.*<a\s+href=[\'"]http://ceur-ws.org/Vol-([0-9]+)[/]?[\'"]>([^<]*)</a>.*''',re.I | re.DOTALL)
         
    def log(self,msg:str):
        '''
        log the given message if debug is on
        
        Args:
            msg(str): the message to log
        '''
        if self.debug:
            print(msg)
            
    def getMatch(self,pattern,text,groupNo:int=1):
        '''
        get the match for the given regular expression for the given text returning the given group number
        
        Args:
            regexp(str): the regular expression to check
            text(str): the text to check
            groupNo(int): the number of the regular expression group to return
            
        Returns:
            str: the matching result or None if no match was found
        '''
        matchResult=pattern.match(text)
        if matchResult:
            return matchResult.group(groupNo)
        else:
            return None
        
    def find(self,startLine:int,needleRegex:str)->int:
        '''
        find the next line with the given regular expression
        
        Args:
            startLine(int): index of the line to start search
            needleRegex(str): the regular expression to search for
            
        Return:
            int: the line number of the line or None if nothing was found
        '''
        pattern=re.compile(needleRegex,re.I)
        lineNo=startLine
        while lineNo<len(self.lines)+1:
            line=self.lines[lineNo-1]
            if pattern.match(line):
                return lineNo
            lineNo+=1
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
            infoValue=infoValue.replace("<BR>","")
            if info=="editors":
                infoValue=html.unescape(infoValue)
            if info in ["urn","url","archive"]:
                href=self.getMatch(self.linkPattern, infoValue, 1)
                if href is not None:
                    infoValue=href
                    if info=="url":
                        volNumber=self.getMatch(self.volPattern, href, 1)
                        if volNumber is not None:
                            volume["number"]=int(volNumber)
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
        
        infoPattern={}
        for prefix,info in [
            ("URN","urn"),
            ("ONLINE","url"),
            ("ARCHIVE","archive"),
            ("Edited by","editors"),
            ("Published on CEUR-WS","pubDate")]:
            infoPattern[info]=re.compile(f"^\s*{prefix}:(.*)")
        for lineIndex in range(fromLine,toLine):
            line=self.lines[lineIndex]
            for info,pattern in infoPattern.items():
                self.getInfo(volume,info,pattern,line)
            volName=self.getMatch(self.volLinkPattern, line, 2)
            if volName is not None:
                if not volName.startswith("http:"):
                    volume["acronym"]=html.unescape(volName)
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
       
            