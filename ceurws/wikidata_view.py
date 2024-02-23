'''
Created on 2024-02-23

@author: wf
'''
from ceurws.view import View

class WikidataView(View):
    """
    Wikidata View
    """
    
    def __init__(self, solution, parent):
        """
        constructor

        Args:
            solution: the solution
            parent: the parent UI container

        """
        self.solution = solution
        self.parent = parent
        self.setup_ui()
        
    def setup_ui(self):
        """
        setup my User Interface elements
        """
        with self.parent:
            pass
    
