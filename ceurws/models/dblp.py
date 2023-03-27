from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DblpAuthor:
    dblp_author_id: str
    label: Optional[str] = None
    wikidata_id: Optional[str] = None
    orcid_id: Optional[str] = None
    gnd_id: Optional[str] = None


@dataclass
class DblpPaper:
    dblp_publication_id: str
    dblp_proceeding_id: Optional[str] = None
    authors: Optional[List[DblpAuthor]]= field(default_factory=list)
    pdf_id: Optional[str] = None

    def __post_init__(self):
        for i, author in enumerate(self.authors):
            if isinstance(author, dict):
                self.authors[i] = DblpAuthor(**author)

