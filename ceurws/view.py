"""
Created on 2024-02-23

@author: wf
"""

from ngwidgets.widgets import Link
from nicegui import ui
from tabulate import tabulate


class View:
    """
    generic View
    """

    noneValue = "-"
    wdPrefix = "http://www.wikidata.org/entity/"
    SYNC_TOOLTIP = "Export to Wikidata"
    SYNC_HINT = "Export to Wikidata needs an ORCID login with the wikidatasync right"
    # a write waits while Wikidata reports replication lag - this may take minutes per volume
    SYNC_TIMEOUT = 4 * 3600.0

    def add_sync_button(self, on_click) -> ui.button:
        """
        add the Export to Wikidata button with its busy indicator

        the button is greyed out with a hint for users without the wikidatasync right,
        the spinner and the status label show a running export

        Args:
            on_click: the handler of the button

        Returns:
            ui.button: the button
        """
        may_sync = self.solution.may_sync_wikidata()
        tooltip = self.SYNC_TOOLTIP if may_sync else self.SYNC_HINT
        with ui.element("div").tooltip(tooltip):
            button = ui.button(icon="web", on_click=on_click).classes("btn btn-primary btn-sm")
        button.set_enabled(may_sync)
        self.sync_spinner = ui.spinner(size="lg")
        self.sync_spinner.set_visibility(False)
        self.sync_status = ui.label()
        return button

    def run_sync(self, func, button: ui.button, busy_text: str, on_result=None) -> None:
        """
        run the given blocking Wikidata export in the background and show the busy state meanwhile

        Args:
            func: the blocking export function
            button: the export button to disable while the export runs
            busy_text: the status text while the export runs
            on_result: called in the user interface context with the return value of func
        """
        self.solution.run_busy(
            func,
            status=self.sync_status,
            button=button,
            spinner=self.sync_spinner,
            on_result=on_result,
            busy_text=busy_text,
            done_text="Wikidata export finished",
            timeout=self.SYNC_TIMEOUT,
        )

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

    def createWdLink(self, qid: str, text: str):
        wd_url = f"{View.wdPrefix}/{qid}"
        link = self.createLink(wd_url, text)
        return link

    def get_dict_as_html_table(self, data_dict) -> str:
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
        if not value or value == View.noneValue:
            if emptyIfNone:
                return ""
            else:
                return View.noneValue

        if value.startswith(View.wdPrefix):
            value = value.replace(View.wdPrefix, "")
        url = formatterUrl + value
        link = self.createLink(url, text)
        return link

    def createItemLink(self, row: dict, key: str, separator: str | None = None) -> str:
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
            for url, label in zip(item_parts, itemLabel_parts, strict=False):
                link = self.createLink(url, label)
                links.append(link)
            itemLink = "<br>".join(links)
        else:
            itemLink = self.createLink(item, itemLabel)
        return itemLink
