"""
Created on 2024-02-23

@author: wf
"""
from ngwidgets.widgets import Link

class View:
    """
    generic View
    """

    noneValue = "-"
    
    def getValue(self, obj, attr):
        value = getattr(obj, attr, View.noneValue)
        if value is None:
            value = View.noneValue
        return value

    def getRowValue(self, row, key):
        value = None
        if key in row:
            value = row[key]
        if value is None:
            value = View.noneValue
        return value
    
    def createLink(self, url: str, text: str):
        """
        create a link from the given url and text

        Args:
            url(str): the url to create a link for
            text(str): the text to add for the link
        """
        link = Link.create(url, text, target="_blank")
        return link


    def createExternalLink(
        self,
        row: dict,
        key: str,
        text: str,
        formatterUrl: str,
        emptyIfNone: bool = False,
    ) -> str:
        """
        create an ExternalLink for the given row entry with the given key, text and formatterUrl

        Args:
            row(dict): the row to extract the value from
            key(str): the key
            text(str): the text to display for the link
            formatterUrl(str): the prefix for the url to use
            emptyIfNone(bool): if True return empty string if value is Display.noneValue

        Returns:
            str - html link for external id
        """
        value = self.getRowValue(row, key)
        wdPrefix = "http://www.wikidata.org/entity/"
        if value.startswith(wdPrefix):
            value = value.replace(wdPrefix, "")
        if value == View.noneValue:
            if emptyIfNone:
                return ""
            else:
                return View.noneValue
        url = formatterUrl + value
        link = self.createLink(url, text)
        return link