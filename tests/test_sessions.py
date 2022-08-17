from tests.basetest import Basetest
from ceurws.ceur_ws import SessionManager

class TestSessions(Basetest):
    """
    Test session manager
    """

    def test_sessions(self):
        sessions=[
            {"volume":2992, "title":"Information Technologies and Intelligent Decision Making Systems II"},
            {"volume":2976, "title": "Digital Infrastructures for Scholarly Content Objects 2021"},
            {"volume":2975, "title": "Novel Approaches with AI and Edge Computing"},  #http://ceur-ws.org/Vol-2975/
            {"volume":2975, "title": "Impact, Metrics and Sustainability"},  #http://ceur-ws.org/Vol-2975/
        ]
        manager=SessionManager()
        manager.fromLoD(sessions)
        withStore=False
        if withStore:
            manager.store()