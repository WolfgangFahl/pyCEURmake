"""
Created on 2024-03-16

@author: wf
"""
 
from sqlmodel import SQLModel,Field
from typing import Optional

class Paper(SQLModel, table=True):
    """
    A paper indexed in DBLP with additional details. The paper URL is used as the unique identifier.
    """
    paper: str = Field(primary_key=True)
    proceeding: str = Field(index=True)
    volume_number: str = Field(index=True)
    title: str
    pdf_url: Optional[str]
    
class Scholar(SQLModel, table=True):
    """
    Represents a scholar with information fetched from DBLP and possibly other sources.
    """
    dblp_author_id: str = Field(primary_key=True)
    label: Optional[str] = None
    wikidata_id: Optional[str] = None
    orcid_id: Optional[str] = None
    gnd_id: Optional[str] = None
    
class Proceeding(SQLModel, table=True):
    """
    A proceeding indexed in DBLP with additional details.
    """
    dblp_publication_id: Optional[str] 
    volume_number: int = Field(primary_key=True)
    title: str
    dblp_event_id: Optional[str] = None

