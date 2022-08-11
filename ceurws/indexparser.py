'''
Created on 11.08.2022

@author: wf
'''
#from pyparsing import makeHTMLTags, SkipTo, htmlComment
import re

class IndexHtmlParser():
    '''
    CEUR-WS Index.html parser
    '''

    def __init__(self,htmlText):
        '''
        Constructor
        '''
        self.htmlText=htmlText
        # soup (in memory is slow)
        # soup = BeautifulSoup(html_page, 'html.parser'
        self.lines=htmlText.split("\n")
        #trStart, trEnd = makeHTMLTags("tr")
        #self.tr = trStart + SkipTo(trEnd).setResultsName("tr") + trEnd.suppress()
        
    def find(self,startLine,needleRegex):
        pattern=re.compile(needleRegex,re.I)
        i=startLine
        while i<len(self.lines):
            line=self.lines[i]
            if pattern.match(line):
                return i
            i+=1
        return None
    
    def findVolume(self,startLine):
        trCount=0
        lineNo=startLine
        while lineNo<len(self.lines):
            trStartLine=self.find(lineNo, "<tr>")
            if trStartLine is None:
                break
            else:
                lineNo=trStartLine+1
                trCount+=1
                if trCount==3:
                    trEndLine=self.find(lineNo+1,"</tr>")
                    return trEndLine
        return None 
            
        
    def parse(self):
        lineNo=self.find(0, '<TABLE id="MAINTABLE"')
        volCount=0
        while lineNo<len(self.lines):
            volLine=self.findVolume(lineNo)
            if volLine is  None:
                break
            else:
                volCount+=1
                print(f"{volCount}:{lineNo}-{volLine}")
                lineNo=volLine+1
       
            