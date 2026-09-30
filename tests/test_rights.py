"""
Created on 2026-09-30

@author: wf
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from ceurws.volume_view import VolumeListView, VolumeView
from ceurws.webserver import CeurWsSolution
from tests.basetest import Basetest


class TestRights(Basetest):
    """
    test that the log pane and the Wikidata sync need the rights log and wikidatasync
    see https://github.com/WolfgangFahl/pyCEURmake/issues/110
    """

    def setUp(self, debug=False, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)

    def get_solution(self, rights: list[str]) -> CeurWsSolution:
        """
        get a solution for a user session with the given rights

        Args:
            rights: the rights of the user - an anonymous visitor has none
        """
        solution = CeurWsSolution.__new__(CeurWsSolution)
        solution.webserver = MagicMock()
        solution.webserver.scholar_login.has_right.side_effect = lambda right: right in rights
        solution.log_view = None
        solution.wdSync = MagicMock()
        solution.wdSync.addProceedingsToWikidata.return_value = MagicMock(qid="Q1")
        return solution

    def get_volume_view(self, solution: CeurWsSolution) -> VolumeView:
        """
        get a volume view with a volume to export
        """
        volume_view = VolumeView(solution, parent=None)
        volume_view.volume = MagicMock(number=4203)
        volume_view.updateWikidataSpan = MagicMock()
        return volume_view

    def get_volume_list_view(self, solution: CeurWsSolution) -> VolumeListView:
        """
        get a volume list view without user interface
        """
        volume_list_view = VolumeListView.__new__(VolumeListView)
        volume_list_view.solution = solution
        volume_list_view.wdSync = solution.wdSync
        volume_list_view.lod_grid = MagicMock()
        volume_list_view.lod_grid.get_selected_rows = AsyncMock(return_value=[])
        return volume_list_view

    def test_rights_of_solution(self):
        """
        test the mapping of the two rights
        """
        cases = [
            ([], False, False),
            (["log"], True, False),
            (["wikidatasync"], False, True),
            (["log", "wikidatasync"], True, True),
        ]
        for rights, expected_log, expected_sync in cases:
            solution = self.get_solution(rights)
            self.assertEqual(expected_log, solution.may_see_log(), rights)
            self.assertEqual(expected_sync, solution.may_sync_wikidata(), rights)

    def test_log_view(self):
        """
        test that the footer only gets a log view for users with the log right
        """
        for rights, expected_with_log in [([], False), (["wikidatasync"], False), (["log"], True)]:
            solution = self.get_solution(rights)
            with patch("ceurws.webserver.InputWebSolution.setup_footer", new_callable=AsyncMock) as setup_footer:
                asyncio.run(solution.setup_footer())
            setup_footer.assert_awaited_once_with(solution, with_log=expected_with_log)

    def test_volume_export(self):
        """
        test that the export of a single volume needs the wikidatasync right
        """
        for rights, expected_calls in [([], 0), (["log"], 0), (["wikidatasync"], 1)]:
            solution = self.get_solution(rights)
            volume_view = self.get_volume_view(solution)
            with patch("ceurws.volume_view.ui") as ui:
                asyncio.run(volume_view.onWikidataButtonClick(None))
            self.assertEqual(expected_calls, solution.wdSync.addProceedingsToWikidata.call_count, rights)
            if expected_calls == 0:
                ui.notify.assert_called_once_with("not authorized for wikidata sync")

    def test_volume_list_sync(self):
        """
        test that the sync of selected volumes needs the wikidatasync right
        """
        for rights, expected_calls in [([], 0), (["log"], 0), (["wikidatasync"], 1)]:
            solution = self.get_solution(rights)
            volume_list_view = self.get_volume_list_view(solution)
            with patch("ceurws.volume_view.ui") as ui, patch("ceurws.volume_view.run") as run:
                run.io_bound = AsyncMock()
                asyncio.run(volume_list_view.onWikidataButtonClick(None))
            self.assertEqual(expected_calls, run.io_bound.await_count, rights)
            if expected_calls == 0:
                ui.notify.assert_called_once_with("not authorized for wikidata sync")
                volume_list_view.lod_grid.get_selected_rows.assert_not_awaited()
