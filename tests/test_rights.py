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
        solution.run_busy = MagicMock()
        return solution

    def add_sync_elements(self, view) -> None:
        """
        give the view the elements that add_sync_button creates
        """
        view.wikidataButton = MagicMock()
        view.sync_status = MagicMock()
        view.sync_spinner = MagicMock()

    def check_busy_call(self, solution: CeurWsSolution, view, busy_text: str) -> None:
        """
        check that the export was started in the background with the busy indicator of the view
        """
        kwargs = solution.run_busy.call_args.kwargs
        self.assertEqual(busy_text, kwargs["busy_text"])
        self.assertIs(view.wikidataButton, kwargs["button"])
        self.assertIs(view.sync_status, kwargs["status"])
        self.assertIs(view.sync_spinner, kwargs["spinner"])
        self.assertEqual(view.SYNC_TIMEOUT, kwargs["timeout"])

    def get_volume_view(self, solution: CeurWsSolution) -> VolumeView:
        """
        get a volume view with a volume to export
        """
        volume_view = VolumeView(solution, parent=None)
        volume_view.volume = MagicMock(number=4203)
        volume_view.updateWikidataSpan = MagicMock()
        self.add_sync_elements(volume_view)
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
        volume_list_view.progress_bar = MagicMock()
        volume_list_view.button_row = MagicMock()
        volume_list_view.log_row = MagicMock()
        volume_list_view.log_view = MagicMock()
        self.add_sync_elements(volume_list_view)
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

    def test_sync_button(self):
        """
        test that the export button is greyed out with a hint without the wikidatasync right
        """
        for rights, expected_enabled, expected_tooltip in [
            ([], False, VolumeView.SYNC_HINT),
            (["log"], False, VolumeView.SYNC_HINT),
            (["wikidatasync"], True, VolumeView.SYNC_TOOLTIP),
        ]:
            solution = self.get_solution(rights)
            volume_view = self.get_volume_view(solution)
            with patch("ceurws.view.ui") as ui:
                button = volume_view.add_sync_button(volume_view.onWikidataButtonClick)
            ui.element.return_value.tooltip.assert_called_once_with(expected_tooltip)
            button.set_enabled.assert_called_once_with(expected_enabled)

    def test_volume_export(self):
        """
        test that the export of a single volume needs the wikidatasync right and runs with a busy indicator
        """
        for rights, expected_calls in [([], 0), (["log"], 0), (["wikidatasync"], 1)]:
            solution = self.get_solution(rights)
            volume_view = self.get_volume_view(solution)
            with patch("ceurws.volume_view.ui") as ui:
                asyncio.run(volume_view.onWikidataButtonClick(None))
            self.assertEqual(expected_calls, solution.run_busy.call_count, rights)
            solution.wdSync.addProceedingsToWikidata.assert_not_called()
            if expected_calls == 0:
                ui.notify.assert_called_once_with("not authorized for wikidata sync")
            else:
                self.check_busy_call(solution, volume_view, "exporting Vol 4203 to Wikidata ...")
                export = solution.run_busy.call_args.args[0]
                on_result = solution.run_busy.call_args.kwargs["on_result"]
                result = export()
                solution.wdSync.addProceedingsToWikidata.assert_called_once()
                self.assertTrue(solution.wdSync.addProceedingsToWikidata.call_args.kwargs["write"])
                with patch("ceurws.volume_view.ui"):
                    on_result(result)
                volume_view.updateWikidataSpan.assert_called_once_with(qId="Q1", volume=volume_view.volume)
                volume_view.wikidataButton.set_enabled.assert_called_once_with(False)

    def test_volume_export_failure(self):
        """
        test that a failing export is handed to the exception handling and shows no result
        """
        solution = self.get_solution(["wikidatasync"])
        solution.handle_exception = MagicMock()
        solution.wdSync.addProceedingsToWikidata.side_effect = RuntimeError("write failed")
        volume_view = self.get_volume_view(solution)
        result = volume_view.export_volume()
        self.assertIsNone(result)
        solution.handle_exception.assert_called_once()
        with patch("ceurws.volume_view.ui") as ui:
            volume_view.on_volume_exported(result)
        ui.notify.assert_not_called()
        volume_view.updateWikidataSpan.assert_not_called()

    def test_volume_list_sync(self):
        """
        test that the sync of selected volumes needs the wikidatasync right and runs with a busy indicator
        """
        for rights, expected_calls in [([], 0), (["log"], 0), (["wikidatasync"], 1)]:
            solution = self.get_solution(rights)
            volume_list_view = self.get_volume_list_view(solution)
            volume_list_view.lod_grid.get_selected_rows = AsyncMock(return_value=[{"#": 4237}, {"#": 4241}])
            with patch("ceurws.volume_view.ui") as ui:
                asyncio.run(volume_list_view.onWikidataButtonClick(None))
            self.assertEqual(expected_calls, solution.run_busy.call_count, rights)
            if expected_calls == 0:
                ui.notify.assert_called_once_with("not authorized for wikidata sync")
                volume_list_view.lod_grid.get_selected_rows.assert_not_awaited()
            else:
                self.check_busy_call(solution, volume_list_view, "syncing 2 volumes with Wikidata ...")

    def test_sync_progress(self):
        """
        test that the progress bar advances by one step per synced volume in ascending volume order
        """
        solution = self.get_solution(["wikidatasync"])
        volume_list_view = self.get_volume_list_view(solution)
        volumes = {number: MagicMock(number=number) for number in (4202, 4237, 4241)}
        solution.wdSync.volumesByNumber = volumes
        volume_list_view.add_or_update_volume_in_wikidata = MagicMock()
        volume_list_view.updateWikidataVolumes([{"#": 4241}, {"#": 4202}, {"#": 4237}])
        self.assertEqual(3, volume_list_view.progress_bar.total)
        volume_list_view.progress_bar.reset.assert_called_once()
        self.assertEqual(3, volume_list_view.progress_bar.update.call_count)
        synced = [call.args[0].number for call in volume_list_view.add_or_update_volume_in_wikidata.call_args_list]
        self.assertEqual([4202, 4237, 4241], synced)
        status_texts = [call.args[0] for call in volume_list_view.sync_status.set_text.call_args_list]
        self.assertEqual("syncing Vol 4241 with Wikidata (3/3) ...", status_texts[-1])
