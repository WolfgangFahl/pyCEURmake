"""
Created on 2023
@author: Tim Holzheim

refactored 2024-03-09 by wf
"""
from dataclasses import field
from typing import List, Optional
from lodstorage.yamlable import lod_storable

@lod_storable
class DblpScholar:
    """
    a scholar indexed by dblp.org
    
    example: Tim Berners-Lee
    https://dblp.org/pid/b/TimBernersLee.html
    
    """
    dblp_author_id: str
    label: Optional[str] = None
    wikidata_id: Optional[str] = None
    orcid_id: Optional[str] = None
    gnd_id: Optional[str] = None

@lod_storable
class DblpPaper:
    """
    a paper indexed by dblp.org
    """
    dblp_publication_id: str
    dblp_proceeding_id: str
    volume_number: int
    title: str
    authors: Optional[List[DblpScholar]] = field(default_factory=list)
    pdf_id: Optional[str] = None

    def __post_init__(self):
        for i, author in enumerate(self.authors):
            if isinstance(author, dict):
                self.authors[i] = DblpScholar(**author)

@lod_storable
class DblpProceeding:
    """
    a proceeding indexed by dblp.org
    """
    dblp_publication_id: str
    volume_number: int
    title: str
    dblp_event_id: Optional[str] = None
    papers: Optional[List[DblpPaper]] = field(default_factory=list)
    editors: Optional[List[DblpScholar]] = field(default_factory=list)

    def __post_init__(self):
        if self.editors:
            for i, editor in enumerate(self.editors):
                if isinstance(editor, dict):
                    self.editors[i] = DblpScholar(**editor)
        if self.papers:
            for i, paper in enumerate(self.papers):
                if isinstance(paper, dict):
                    self.papers[i] = DblpPaper(**paper)
