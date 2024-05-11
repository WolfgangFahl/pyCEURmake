"""
Created on 2024-03-17

CEUR Workshop Proceedings (CEUR-WS.org)

Metamodel
@author: wf
"""

from datetime import date, datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Volume(SQLModel, table=True):  # type: ignore
    """
    a single CEUR-WS Volume
    """

    __tablename__ = "volumes"

    fromLine: Optional[int] = Field(default=None)
    toLine: Optional[int] = Field(default=None)
    valid: Optional[int] = Field(default=None)
    url: Optional[str] = Field(default=None)
    acronym: Optional[str] = Field(default=None)
    title: Optional[str] = Field(default=None)
    seealso: Optional[str] = Field(default=None)
    editors: Optional[str] = Field(default=None)
    submittedBy: Optional[str] = Field(default=None)
    published: Optional[str] = Field(default=None)
    pubDate: Optional[datetime] = Field(default=None)
    number: int = Field(primary_key=True)
    archive: Optional[str] = Field(default=None)
    desc: Optional[str] = Field(alias="description", default=None)  # 'desc' is a SQL keyword, so it's aliased
    h1: Optional[str] = Field(default=None)
    h3: Optional[str] = Field(default=None)
    volname: Optional[str] = Field(default=None)
    homepage: Optional[str] = Field(default=None)
    year: Optional[str] = Field(default=None)
    urn: Optional[str] = Field(default=None)
    # vol_number: Optional[int] = Field(default=None)
    loctime: Optional[str] = Field(default=None)
    volume_number: Optional[str] = Field(default=None)
    voltitle: Optional[str] = Field(default=None)
    dateFrom: Optional[date] = Field(default=None)
    dateTo: Optional[date] = Field(default=None)
    city: Optional[str] = Field(default=None)
    cityWikidataId: Optional[str] = Field(default=None)
    country: Optional[str] = Field(default=None)
    countryWikidataId: Optional[str] = Field(default=None)
    urn_check_digit: Optional[int] = Field(default=None)
    urn_ok: Optional[int] = Field(default=None)
    ceurpubdate: Optional[str] = Field(default=None)
    colocated: Optional[str] = Field(default=None)
    virtualEvent: Optional[int] = Field(default=None)
    tdtitle: Optional[str] = Field(default=None)


class Paper(SQLModel, table=True):  # type: ignore
    """
    Represents a paper with details such as authors, volume number, and title.
    """

    __tablename__ = "papers"
    authors: Optional[str] = Field(default=None, index=False)
    vol_number: Optional[int] = Field(default=None, index=True)
    pdf_name: Optional[str] = Field(default=None, index=False)
    id: str = Field(primary_key=True)
    title: Optional[str] = Field(default=None, index=False)
    pages: Optional[str] = Field(default=None, index=False)
    fail: Optional[str] = Field(default=None, index=False)
