"""
Created on 2026-09-30

@author: wf
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from ceurws.volume_view import VolumeListView, VolumeView
from ceurws.webserver import CeurWsSolution
from ceurws.wikidata_lag import WikidataLag
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
        solution.args = MagicMock(wikidata_timeout=5.0)
        return solution

    def add_sync_elements(self, view) -> None:
        """
        give the view the elements that add_sync_button creates
        """
        view.wikidataButton = MagicMock()
        view.sync_status = MagicMock()
        view.sync_spinner = MagicMock()
        self.set_wikidata_ready(view, [True])

    def set_wikidata_ready(self, view, ready_flags: list[bool]) -> None:
        """
        let the lag check of the view answer with the given ready flags, the last one repeats
        """
        flags = list(ready_flags)

        def lag_check(_container, _what):
            ready = flags.pop(0) if len(flags) > 1 else flags[0]
            wikidata_lag = WikidataLag(timeout_minutes=5.0)
            wikidata_lag.ready = ready
            return wikidata_lag

        view.wait_for_wikidata = MagicMock(side_effect=lag_check)

    def check_busy_call(self, solution: CeurWsSolution, view, busy_text: str, volume_count: int) -> None:
        """
        check that the export was started in the background with the busy indicator of the view
        """
        kwargs = solution.run_busy.call_args.kwargs
        self.assertEqual(busy_text, kwargs["busy_text"])
        self.assertIs(view.wikidataButton, kwargs["button"])
        self.assertIs(view.sync_status, kwargs["status"])
        self.assertIs(view.sync_spinner, kwargs["spinner"])
        self.assertEqual(volume_count * 2 * 5.0 * 60, kwargs["timeout"])

    def get_volume_view(self, solution: CeurWsSolution) -> VolumeView:
        """
        get a volume view with a volume to export
        """
        volume_view = VolumeView(solution, parent=None)
        volume_view.volume = MagicMock(number=4203)
        volume_view.updateWikidataSpan = MagicMock()
        volume_view.volumeToolBar = MagicMock()
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
        volume_list_view.dry_run = False
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
                self.check_busy_call(solution, volume_view, "Exporting Vol 4203 to Wikidata …", 1)
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
                self.check_busy_call(solution, volume_list_view, "Syncing 2 volumes with Wikidata …", 2)

    def test_sync_progress(self):
        """
        test that the progress bar advances by one step per synced volume in ascending volume order
        """
        solution = self.get_solution(["wikidatasync"])
        volume_list_view = self.get_volume_list_view(solution)
        volumes = {number: MagicMock(number=number) for number in (4202, 4237, 4241)}
        solution.wdSync.volumesByNumber = volumes
        volume_list_view.add_or_update_volume_in_wikidata = MagicMock()
        summary = volume_list_view.updateWikidataVolumes([{"#": 4241}, {"#": 4202}, {"#": 4237}])
        self.assertEqual("Wikidata sync finished: 3 of 3 volumes processed", summary)
        self.assertEqual(3, volume_list_view.wait_for_wikidata.call_count)
        self.assertEqual(3, volume_list_view.progress_bar.total)
        volume_list_view.progress_bar.reset.assert_called_once()
        self.assertEqual(3, volume_list_view.progress_bar.update.call_count)
        synced = [call.args[0].number for call in volume_list_view.add_or_update_volume_in_wikidata.call_args_list]
        self.assertEqual([4202, 4237, 4241], synced)
        status_texts = [call.args[0] for call in volume_list_view.sync_status.set_text.call_args_list]
        self.assertEqual("Syncing Vol 4241 (3 of 3) with Wikidata …", status_texts[-1])

    def test_sync_stops_on_lag(self):
        """
        test that the sync stops with a summary when Wikidata does not accept writes in time
        """
        solution = self.get_solution(["wikidatasync"])
        volume_list_view = self.get_volume_list_view(solution)
        self.set_wikidata_ready(volume_list_view, [True, False])
        solution.wdSync.volumesByNumber = {number: MagicMock(number=number) for number in (4202, 4237, 4241)}
        volume_list_view.add_or_update_volume_in_wikidata = MagicMock()
        summary = volume_list_view.updateWikidataVolumes([{"#": 4241}, {"#": 4202}, {"#": 4237}])
        expected = (
            "Wikidata lag stayed above the 5 seconds max lag for edits for 5 minutes. "
            "Sync stopped at Vol 4237; 2 of 3 volumes are not synced. Please try again later."
        )
        self.assertEqual(expected, summary)
        self.assertEqual(1, volume_list_view.add_or_update_volume_in_wikidata.call_count)
        self.assertEqual(1, volume_list_view.progress_bar.update.call_count)
        with patch("ceurws.volume_view.ui") as ui:
            volume_list_view.on_volumes_synced(summary)
        ui.notify.assert_called_once_with(expected)
        volume_list_view.sync_status.set_text.assert_called_with(expected)

    def test_dry_run_skips_lag_check(self):
        """
        test that a dry run does not wait for Wikidata
        """
        solution = self.get_solution(["wikidatasync"])
        volume_list_view = self.get_volume_list_view(solution)
        volume_list_view.dry_run = True
        self.set_wikidata_ready(volume_list_view, [False])
        solution.wdSync.volumesByNumber = {4237: MagicMock(number=4237)}
        volume_list_view.add_or_update_volume_in_wikidata = MagicMock()
        summary = volume_list_view.updateWikidataVolumes([{"#": 4237}])
        self.assertEqual("Wikidata sync finished: 1 of 1 volumes processed", summary)
        volume_list_view.wait_for_wikidata.assert_not_called()

    def test_volume_export_stops_on_lag(self):
        """
        test that a single volume is not exported when Wikidata does not accept writes in time
        """
        solution = self.get_solution(["wikidatasync"])
        volume_view = self.get_volume_view(solution)
        self.set_wikidata_ready(volume_view, [False])
        result = volume_view.export_volume()
        self.assertIsNone(result)
        solution.wdSync.addProceedingsToWikidata.assert_not_called()
        expected = (
            "Wikidata lag stayed above the 5 seconds max lag for edits for 5 minutes. "
            "Vol 4203 was not exported. Please try again later."
        )
        self.assertEqual(expected, volume_view.export_hint)
        with patch("ceurws.volume_view.ui") as ui:
            volume_view.on_volume_exported(result)
        ui.notify.assert_called_once_with(expected)
        volume_view.sync_status.set_text.assert_called_with(expected)

    def test_wait_is_shown(self):
        """
        test that the wait for Wikidata shows lag, limit and elapsed time in the status label
        """
        solution = self.get_solution(["wikidatasync"])
        volume_view = VolumeView(solution, parent=None)
        volume_view.sync_status = MagicMock()
        container = MagicMock()
        with (
            patch.object(WikidataLag, "get_lag", side_effect=[9.3, 4.1]),
            patch("ceurws.wikidata_lag.time.sleep") as sleep,
        ):
            wikidata_lag = volume_view.wait_for_wikidata(container, "Vol 4237 (1 of 2)")
        self.assertTrue(wikidata_lag.ready)
        sleep.assert_called_once_with(10.0)
        status_text = volume_view.sync_status.set_text.call_args.args[0]
        expected = (
            "Vol 4237 (1 of 2): Wikidata lag is 9.3 seconds, more than the 5 seconds max lag for edits. "
            "Waiting, minute 1 of 5 …"
        )
        self.assertEqual(expected, status_text)
