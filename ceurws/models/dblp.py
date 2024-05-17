"""
Created on 2023
@author: Tim Holzheim

refactored 2024-03-09 by wf
"""

from dataclasses import field

from lodstorage.yamlable import lod_storable


@lod_storable
class DblpScholar:
    """
    a scholar indexed by dblp.org

    example: Tim Berners-Lee
    https://dblp.org/pid/b/TimBernersLee.html

    """

    dblp_author_id: str
    label: str | None = None
    wikidata_id: str | None = None
    orcid_id: str | None = None
    gnd_id: str | None = None


@lod_storable
class DblpPaper:
    """
    a paper indexed by dblp.org
    """

    dblp_publication_id: str
    dblp_proceeding_id: str
    volume_number: int
    title: str
    authors: list[DblpScholar] | None = field(default_factory=list)
    pdf_id: str | None = None

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
    dblp_event_id: str | None = None
    papers: list[DblpPaper] | None = field(default_factory=list)
    editors: list[DblpScholar] | None = field(default_factory=list)

    def __post_init__(self):
        if self.editors:
            for i, editor in enumerate(self.editors):
                if isinstance(editor, dict):
                    self.editors[i] = DblpScholar(**editor)
        if self.papers:
            for i, paper in enumerate(self.papers):
                if isinstance(paper, dict):
                    self.papers[i] = DblpPaper(**paper)
