"""
Created on 2024-02-23

@author: wf
"""
from ngwidgets.widgets import Link
from tabulate import tabulate

class View:
    """
    generic View
    """

    noneValue = "-"
    wdPrefix = "http://www.wikidata.org/entity/"

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
    
    def createWdLink(self,qid:str,text:str):
        wd_url=f"{View.wdPrefix}/{qid}"
        link=self.createLink(wd_url, text)
        return link
    
    def get_dict_as_html_table(self,data_dict)->str:
        # Convert the dictionary to a list of lists for tabulate
        data_list = [[key, value] for key, value in data_dict.items()]
        
        # Generate the HTML table
        html_table = tabulate(data_list, tablefmt="html", headers=["Key", "Value"])
        return html_table
        
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
        if not value:
            if emptyIfNone:
                return ""
            else:
                return View.noneValue
        
        if value.startswith(View.wdPrefix):
            value = value.replace(View.wdPrefix, "")
        url = formatterUrl + value
        link = self.createLink(url, text)
        return link
    
    def createItemLink(self, row: dict, key: str, separator: str = None) -> str:
        """
        create an item link
        Args:
            row: row object with the data
            key: key of the value for which the link is created
            separator: If not None split the value on the separator and create multiple links
        """
        value = self.getRowValue(row, key)
        if value == View.noneValue:
            return value
        item = row[key]
        itemLabel = row[f"{key}Label"]
        itemLink = ""
        if separator is not None:
            item_parts = item.split(separator)
            itemLabel_parts = itemLabel.split(separator)
            links = []
            for url, label in zip(item_parts, itemLabel_parts):
                link = self.createLink(url, label)
                links.append(link)
            itemLink = "<br>".join(links)
        else:
            itemLink = self.createLink(item, itemLabel)
        return itemLink
