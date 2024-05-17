"""
Created on 2024-03-16

@author: wf
"""

from sqlmodel import Field, SQLModel


class Scholar(SQLModel, table=True):  # type: ignore
    """
    Represents a scholar with information fetched from DBLP and possibly other sources.
    """

    dblp_author_id: str = Field(primary_key=True)
    label: str | None = None
    wikidata_id: str | None = None
    orcid_id: str | None = None
    gnd_id: str | None = None


class Paper(SQLModel, table=True):  # type: ignore
    """
    A paper indexed in DBLP with additional details. The paper URL is used as the unique identifier.
    """

    paper: str = Field(primary_key=True)
    proceeding: str | None = Field(foreign_key="proceeding.proceeding")
    volume_number: str = Field(index=True)
    title: str
    pdf_url: str | None = None


class Proceeding(SQLModel, table=True):  # type: ignore
    """
    A proceeding indexed in DBLP with additional details.
    """

    proceeding: str = Field(primary_key=True)
    volume_number: int = Field(index=True)
    title: str
    dblp_event_id: str | None = None


class Editorship(SQLModel, table=True):  # type: ignore
    """
    Represents the relationship between a scholar and a proceeding, indicating the scholar's role as an editor.
    """

    volume_number: int = Field(foreign_key="proceeding.volume_number", primary_key=True)
    dblp_author_id: str = Field(foreign_key="scholar.dblp_author_id", primary_key=True)


class Authorship(SQLModel, table=True):  # type: ignore
    """
    Represents the relationship between a scholar and a paper, capturing the authorship details.
    """

    paper: str = Field(foreign_key="paper.paper", primary_key=True)
    dblp_author_id: str = Field(foreign_key="scholar.dblp_author_id", primary_key=True)
