"""
Created on 2024-03-17

CEUR Workshop Proceedings (CEUR-WS.org)

Metamodel
@author: wf
"""

from datetime import date, datetime

from sqlmodel import Field, SQLModel


class Volume(SQLModel, table=True):  # type: ignore
    """
    a single CEUR-WS Volume
    """

    __tablename__ = "volumes"

    fromLine: int | None = Field(default=None)
    toLine: int | None = Field(default=None)
    valid: int | None = Field(default=None)
    url: str | None = Field(default=None)
    acronym: str | None = Field(default=None)
    title: str | None = Field(default=None)
    seealso: str | None = Field(default=None)
    editors: str | None = Field(default=None)
    submittedBy: str | None = Field(default=None)
    published: str | None = Field(default=None)
    pubDate: datetime | None = Field(default=None)
    number: int = Field(primary_key=True)
    archive: str | None = Field(default=None)
    desc: str | None = Field(alias="description", default=None)  # 'desc' is a SQL keyword, so it's aliased
    h1: str | None = Field(default=None)
    h3: str | None = Field(default=None)
    volname: str | None = Field(default=None)
    homepage: str | None = Field(default=None)
    year: str | None = Field(default=None)
    urn: str | None = Field(default=None)
    # vol_number: Optional[int] = Field(default=None)
    loctime: str | None = Field(default=None)
    volume_number: str | None = Field(default=None)
    voltitle: str | None = Field(default=None)
    dateFrom: date | None = Field(default=None)
    dateTo: date | None = Field(default=None)
    city: str | None = Field(default=None)
    cityWikidataId: str | None = Field(default=None)
    country: str | None = Field(default=None)
    countryWikidataId: str | None = Field(default=None)
    urn_check_digit: int | None = Field(default=None)
    urn_ok: int | None = Field(default=None)
    ceurpubdate: str | None = Field(default=None)
    colocated: str | None = Field(default=None)
    virtualEvent: int | None = Field(default=None)
    tdtitle: str | None = Field(default=None)


class Paper(SQLModel, table=True):  # type: ignore
    """
    Represents a paper with details such as authors, volume number, and title.
    """

    __tablename__ = "papers"
    authors: str | None = Field(default=None, index=False)
    vol_number: int | None = Field(default=None, index=True)
    pdf_name: str | None = Field(default=None, index=False)
    id: str = Field(primary_key=True)
    title: str | None = Field(default=None, index=False)
    pages: str | None = Field(default=None, index=False)
    fail: str | None = Field(default=None, index=False)
