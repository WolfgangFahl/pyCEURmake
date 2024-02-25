"""
Created on 11.08.2022

@author: wf
"""
import datetime
import html
import re

from ceurws.textparser import Textparser
from ngwidgets.progress import Progressbar

class ParserConfig:
    """
    parser configuration
    """
    def __init__(self,
        progress_bar:Progressbar=None,
        down_to_volume:int=1,
        force_download:bool=False,
        verbose: bool = False,
        debug:bool=False):
        """
        Initializes the ParserConfig with a progress bar, volume threshold, and debug mode setting.

        Args:
            progress_bar (Progressbar): An instance of a Progressbar class to be used for showing progress during parsing.
            down_to_volume (int, optional): The volume threshold for parsing. Only volumes equal to or less than this value will be considered. Defaults to 1.
            force_download(bool): if True download the file to parse
            verbose(bool): if True give verbose feedback
            debug (bool, optional): Indicates whether debugging mode is enabled. If True, additional debug information will be provided during parsing. Defaults to False.
        """
        self.progress_bar=progress_bar
        self.down_to_volume=down_to_volume
        self.force_download=force_download
        self.verbose=verbose
        self.debug=debug
    

class IndexHtmlParser(Textparser):
    """
    CEUR-WS Index.html parser
    """

    def __init__(self, htmlText, config:ParserConfig=None):
        """
        Constructor

        Args:
            htmlText(str): the HTML text of the index page
        """
        if config is None:
            config=ParserConfig()
        self.config=config
        Textparser.__init__(self, debug=config.debug)
        self.htmlText = htmlText
        # soup (in memory is slow)
        # soup = BeautifulSoup(html_page, 'html.parser'
        self.lines = htmlText.split("\n")
        # trStart, trEnd = makeHTMLTags("tr")
        # self.tr = trStart + SkipTo(trEnd).setResultsName("tr") + trEnd.suppress()
        self.linkPattern = re.compile(r""".*href=[\'"]?([^\'" >]+).*""", re.I)
        self.volPattern = re.compile("http://ceur-ws.org/Vol-([0-9]+)")
        self.volLinkPattern = re.compile(
            r""".*<a\s+href=[\'"]http://ceur-ws.org/Vol-([0-9]+)[/]?[\'"]>([^<]*)</a>.*""",
            re.I | re.DOTALL,
        )
        # Pre-compile patterns used in find and findVolume
        self.thColspanPattern = re.compile(r"^.*<th\s*colspan", re.I)
        self.trStartPattern = re.compile(r"^\s*<tr>", re.I)
        self.trEndPattern = re.compile(r"^\s*</tr>", re.I)
        # Pre-compile patterns used in setVolumeTitle
        self.editedByPattern = re.compile("Edited by:")
        self.tdBgColorPattern = re.compile("<td bgcolor", re.I)

    def find(self, startLine: int, compiledPattern, step: int = 1) -> int:
        """
        find the next line with the given compiled regular expression pattern

        Args:
            startLine(int): index of the line to start search
            compiledPattern(re.Pattern): the compiled regular expression pattern to search for
            step(int): the steps to take e.g. +1 for forward -1 for backwards

        Return:
            int: the line number of the line or None if nothing was found
        """
        lineNo = startLine
        while 0 < lineNo < len(self.lines) + 1:
            line = self.lines[lineNo - 1]
            if compiledPattern.match(line):
                return lineNo
            lineNo += step
        return None

    def findVolume(
        self, volCount: int, startLine: int, expectedTr: int = 3, progress: int = 10
    ) -> int:
        """
        find Volume lines from the given startLine

        Args:
            volCount(int): the volumeCount before the startLine
            startLine(int): index of the line to search
            expectedTr(int): number of <tr> tags expected
            progress(int): how often to show the progress

        Returns:
            endLine of the volume html or None
        """
        trStartLine = self.find(startLine, self.thColspanPattern)
        if trStartLine is not None:
            lineNo = trStartLine + 1
            trCount = 1
            while lineNo < len(self.lines):
                trLine = self.find(lineNo, self.trStartPattern)
                if trLine is None:
                    break
                else:
                    lineNo = trLine + 1
                    trCount += 1
                    if trCount == expectedTr:
                        trEndLine = self.find(lineNo + 1, self.trEndPattern)
                        if volCount % progress == 0:
                            if self.config.verbose:
                                print(
                                    f"volume count {volCount+1:4}: lines {trStartLine:6}-{trEndLine:6}"
                                )
                        return trStartLine, trEndLine
        return None, None

    def setVolumeNumber(self, volume, href):
        """
        set the volumen number
        """
        if href is None:
            return
        volNumber = self.getMatch(self.volPattern, href, 1)
        if volNumber is not None:
            volume["number"] = int(volNumber)

    def setVolumeName(self, volume, line):
        """
        set the volume name
        """
        volName = self.getMatch(self.volLinkPattern, line, 2)
        if volName is not None:
            valid = True
            if not volName.startswith("http:"):
                invalidKeys = ["deleted upon editor request", "Not used"]
                for invalidKey in invalidKeys:
                    if invalidKey in volName:
                        href = self.getMatch(self.linkPattern, line, 1)
                        self.setVolumeNumber(volume, href)
                        valid = False
                volume["valid"] = valid
                if valid:
                    volName = html.unescape(volName)
                    volName = Textparser.sanitize(volName)
                    volume["volname"] = volName

    def setVolumeTitle(self, volume: dict, lineIndex: int):
        """
        set the volume title

        Args:
            volume(dict): the volumeRecord to modify
            lineIndex: where to start setting the volumeTitle
        """
        editedByLine = self.find(lineIndex, self.editedByPattern)
        if editedByLine is not None:
            tdLine = self.find(editedByLine, self.tdBgColorPattern, step=-1)
            if tdLine is not None:
                tdIndex = tdLine - 1
                title = ""
                delim = ""
                while tdIndex < len(self.lines):
                    line = self.lines[tdIndex]
                    if line.startswith("Edited by:"):
                        break
                    for tag in [
                        '<TD bgcolor="#FFFFFF">&nbsp;</TD><TD bgcolor="#FFFFFF">',
                        '<TD bgcolor="#FFFFFF">',
                        '<td bgcolor="#FFFFFF">',
                        "<BR>",
                        "<br>",
                    ]:
                        line = line.replace(tag, "")
                    line = line.replace("\r", " ")
                    title += line + delim
                    delim = " "
                    tdIndex += 1
                volume["tdtitle"] = html.unescape(title).strip()

    def setSeeAlsoVolumes(self, volume: dict, firstLine: int, lastLine: int):
        """
        Extract and set the volume numbers form the see also list
        Example result {"seealso": ["Vol-3067"]}

        Args:
            volume: the volumeRecord to modify
            lineIndex: where to start setting the volumeTitle
        """
        volumes = []
        see_also = ""
        for line in range(firstLine, lastLine):
            see_also += self.lines[line]
        see_also_section = re.search(
            r"see also:(.*?)</font>", see_also, re.DOTALL | re.IGNORECASE
        )

        if see_also_section:
            # Extract the volumes using regex from the see also section
            volumes = re.findall(
                r'<a href="#(Vol-\d+)">', see_also_section.group(1), re.IGNORECASE
            )
        volume["seealso"] = volumes

    def getInfo(self, volume: dict, info: str, pattern, line: str):
        """
        get the info for the given patterns trying to match the pattern on
        the given line

        Args:
            volume(dict): the result dict
            info(str): the name of the dict key to fill
            pattern(regexp): the regular expression to check
            line(str): the line to check
        """
        infoValue = self.getMatch(pattern, line, 1)
        if infoValue is not None:
            for delim in ["<BR>", "<br>"]:
                infoValue = infoValue.replace(delim, "")
            infoValue = infoValue.strip()
            if info in ["editors", "submittedBy"]:
                infoValue = html.unescape(infoValue)
            if info == "pubDate":
                try:
                    infoValue = datetime.datetime.strptime(infoValue, "%d-%b-%Y")
                    published = infoValue.strftime("%Y-%m-%d")
                    volume["published"] = published
                    volume["year"] = infoValue.year
                except ValueError as ve:
                    msg = f"pubDate: {infoValue} of {volume} parsing failed with {ve}"
                    self.log(msg)
            if info in ["urn", "url", "archive"]:
                href = self.getMatch(self.linkPattern, infoValue, 1)
                if href is not None:
                    infoValue = href
                    if info == "url":
                        self.setVolumeNumber(volume, href)
                    if info == "urn":
                        infoValue = href.replace("https://nbn-resolving.org/", "")
            volume[info] = infoValue

    def parseVolume(self, volCount: int, fromLine: int, toLine: int, verbose: bool):
        """
        parse a volume from the given line range
        """
        lineCount = toLine - fromLine
        volume = {}
        volume["fromLine"] = fromLine
        volume["toLine"] = toLine
        volume["valid"] = False
        volume["url"] = None
        volume["acronym"] = None
        volume["title"] = None
        volume["loctime"] = None
        self.setVolumeTitle(volume, fromLine)
        self.setSeeAlsoVolumes(volume, fromLine, toLine)

        infoPattern = {}
        infoMappings = [
            ("URN", "urn"),
            ("ONLINE", "url"),
            ("ARCHIVE", "archive"),
            ("Edited by", "editors"),
            ("Submitted by", "submittedBy"),
            ("Published on CEUR-WS", "pubDate"),
        ]
        for prefix, info in infoMappings:
            infoPattern[info] = re.compile(f"^\s*{prefix}:(.*)")
        for lineIndex in range(fromLine, toLine):
            line = self.lines[lineIndex]
            for info, pattern in infoPattern.items():
                self.getInfo(volume, info, pattern, line)
            self.setVolumeName(volume, line)
            if verbose:
                print(line)
        volumeNumber = volume.get("number", "?")
        acronym = volume.get("acronym", "?")
        self.log(f"{volumeNumber:4}-{volCount:4}:{fromLine}+{lineCount} {acronym}")
        return volume

    def parse(self):
        """
        parse my html code for Volume info
        """
        # Compile the regex pattern right before its usage
        mainTablePattern = re.compile(r'\s*<TABLE id="MAINTABLE"', re.I)
        lineNo = self.find(1, mainTablePattern)
        volCount = 0
        volumes = {}
        while lineNo < len(self.lines):
            expectedTr = 3
            volStartLine, volEndLine = self.findVolume(
                volCount, lineNo, expectedTr=expectedTr
            )
            if volStartLine is None:
                break
            else:
                volCount += 1
                volume = self.parseVolume(
                    volCount, volStartLine, volEndLine, verbose=self.config.verbose
                )
                # synchronize on <tr><th and not on end since trailing TR might be missing
                lineNo = volStartLine + 1
                if "number" in volume:
                    volume_number=volume["number"]
                    if volume_number<self.config.down_to_volume:
                        break
                    volumes[volume_number] = volume
                    if self.config.progress_bar:
                        self.config.progress_bar.update()
                else:
                    self.log(f"volume not found for volume at {volStartLine}")
        return volumes