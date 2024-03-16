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

