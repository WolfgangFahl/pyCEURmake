from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DblpScholar:
    dblp_author_id: str
    label: Optional[str] = None
    wikidata_id: Optional[str] = None
    orcid_id: Optional[str] = None
    gnd_id: Optional[str] = None


@dataclass
class DblpPaper:
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

@dataclass
class DblpProceeding:
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
