"""
Created on 2024-03-09

@author: wf
"""
import dataclasses
from dataclasses import dataclass
import os
from lodstorage.sparql import SPARQL
from lodstorage.cache import CacheManager
from ceurws.models.dblp import DblpPaper, DblpProceeding, DblpScholar
from lodstorage.query import  QueryManager
from lodstorage.lod import LOD
from itertools import groupby
from urllib.error import HTTPError
from typing import Dict, List, Union

class DblpManager:
    """
    Manage DBLP entities.
    
    Attributes:
        endpoint (DblpEndpoint): The endpoint for DBLP queries.
        cache_name (str): The name of the cache to use.
        query_name (str): The name of the query to execute.
    """
    
    def __init__(self, endpoint: 'DblpEndpoint', cache_name: str, query_name: str):
        """
        Initializes the DBLP Manager with the given endpoint, cache name, and query name.

        Args:
            endpoint (DblpEndpoint): The endpoint for DBLP queries.
            cache_name (str): The name of the cache to use.
            query_name (str): The name of the query to execute.
        """
        self.endpoint = endpoint
        self.cache_name = cache_name
        self.query_name = query_name
        
    def load(self, force_query: bool = False):
        """
        Loads a list of dictionaries from the DBLP endpoint.

        Args:
            force_query (bool): If True, forces a new query to the endpoint. Defaults to False.
        """
        self.lod = self.endpoint.get_lod(self.cache_name, self.query_name, force_query=force_query)

class DblpVolumes(DblpManager):
    """
    Manage all DBLP indexed volumes.
    """
    
    def __init__(self, endpoint: 'DblpEndpoint'):
        """
        Initializes the DBLP Volumes manager with the given endpoint.

        Args:
            endpoint (DblpEndpoint): The endpoint for DBLP queries.
        """
        # Call the super constructor with specific cache and query names for volumes
        super().__init__(endpoint, "dblp/volumes", "CEUR-WS all Volumes")
        
    def load(self, force_query: bool = False):
        """
        load my volumes
        """
        super().load(force_query=force_query)
    
class DblpAuthors(DblpManager):
    """
    Manage all authors of DBLP indexed volumes.
    """
    
    def __init__(self, endpoint: 'DblpEndpoint'):
        """
        Initializes the DBLP Authors manager with the given endpoint.

        Args:
            endpoint (DblpEndpoint): The endpoint for DBLP queries.
        """
        # Call the super constructor with specific cache and query names for volumes
        super().__init__(endpoint, "dblp/authors","CEUR-WS Paper Authors")
        
    def load(self, force_query: bool = False):
        """
        load my authors
        """
        super().load(force_query=force_query)
        self.authors = []
        for d in self.lod:
            author = DblpScholar(**d)
            self.authors.append(author)
                           
class DblpEditors(DblpManager):
    """
    Manage all editors of DBLP indexed volumes.
    """
    
    def __init__(self, endpoint: 'DblpEndpoint'):
        """
        Initializes the DBLP Editors manager with the given endpoint.

        Args:
            endpoint (DblpEndpoint): The endpoint for DBLP queries.
        """
        # Call the super constructor with specific cache and query names for volumes
        super().__init__(endpoint, "dblp/editors","CEUR-WS all Editors")
        
    def load(self, force_query: bool = False):
        """
        load my editors
        """
        super().load(force_query=force_query)
        self.editors = []
        for d in self.lod:
            editor = DblpScholar(**d)
            self.editors.append(editor)
    
class DblpEndpoint:
    """
    provides queries and a dblp endpoint to execute them
    """

    DBLP_REC_PREFIX = "https://dblp.org/rec/"
    DBLP_EVENT_PREFIX = "https://dblp.org/db/"

    def __init__(self, endpoint):
        """
        constructor
        """
        self.sparql = SPARQL(endpoint)
        path = os.path.dirname(__file__)
        qYamlFile = f"{path}/resources/queries/dblp.yaml"
        if os.path.isfile(qYamlFile):
            self.qm = QueryManager(lang="sparql", queriesPath=qYamlFile)
        # there is one cache manager for all our json caches
        self.cache_manager = CacheManager("ceurws")
        # Map cache names to their respective functions in DblpEndpoint
        self.cache_functions = {
            "dblp/authors": self.get_all_ceur_authors,
            "dblp/editors": self.get_all_ceur_editors,
            "dblp/papers": self.get_all_ceur_papers,
            "dblp/volumes": self.get_all_ceur_proceedings,
        }
        
    def get_lod(self,
        cache_name:str,
        query_name:str,
        force_query: bool = False)->List:
        """
        get the list of dicts for the given cache and query names 
        optionally forcing a query
        """
        cache=self.cache_manager.get_cache_by_name(cache_name)
        if cache.is_stored and not force_query:
            lod=self.cache_manager.load(cache_name)
        else:
            query = self.qm.queriesByName[query_name]
            lod=self.sparql.queryAsListOfDicts(query.query)
            self.cache_manager.store(cache_name, lod)
        return lod


    def get_all_ceur_authors(self, force_query: bool = False) -> List[DblpScholar]:
        """
        Get all authors that have published a paper in CEUR-WS from dblp

        Args:
            force_query(bool): if True force query
        """
        dblp_authors=DblpAuthors(endpoint=self)
        dblp_authors.load(force_query)
        return dblp_authors.authors

    def get_all_ceur_editors(self, force_query: bool = False) -> List[DblpScholar]:
        """
        Get all authors that have published a paper in CEUR-WS from dblp

        Args:
            force_query(bool): if True force query

        """
        dblp_editors=DblpEditors(endpoint=self)
        dblp_editors.load(force_query)
        return dblp_editors.editors

    def get_all_ceur_papers(self, force_query: bool = False) -> List[DblpPaper]:
        """
        Get all papers published in CEUR-WS from dblp

        Args:
            force_query(bool): if True force query
        """
        query = self.qm.queriesByName["CEUR-WS all Papers"]
        cache_name = "dblp/papers"
        papers = []
        if not force_query:
            lod = self.cache_manager.load(cache_name)
            if lod:
                papers = [DblpPaper(**d) for d in lod]
        if force_query or lod is None:
            lod = self.sparql.queryAsListOfDicts(query.query)
            authors = self.get_all_ceur_authors(force_query)
            authorsById = {a.dblp_author_id: a for a in authors}
            papers = []
            for d in lod:
                pdf_id = d.get("pdf_url", None)
                if pdf_id and isinstance(pdf_id, str):
                    pdf_id = pdf_id.replace("http://ceur-ws.org/", "")
                    pdf_id = pdf_id.replace("https://ceur-ws.org/", "")
                    pdf_id = pdf_id.replace(".pdf", "")
                authors = []
                # get the authors string
                authors_str = d.get("author", "")
                # >;<  qlever quirk until 2023-12
                if ">;<" in authors_str:
                    delim = ">;<"
                else:
                    delim = ";"
                for dblp_author_id in authors_str.split(delim):  #
                    author = authorsById.get(dblp_author_id, None)
                    if author:
                        authors.append(author)
                paper = DblpPaper(
                    dblp_publication_id=d.get("paper"),
                    volume_number=int(d.get("volume_number")),
                    dblp_proceeding_id=d.get("proceeding"),
                    title=d.get("title"),
                    pdf_id=pdf_id,
                    authors=authors,
                )
                papers.append(paper)
            self.cache_manager.store(
                cache_name, [dataclasses.asdict(paper) for paper in papers]
            )
            papers_by_volume = LOD.getLookup(
                papers, "volume_number", withDuplicates=True
            )
            for volume_number, vol_papers in papers_by_volume.items():
                self.cache_manager.store(
                    f"dblp/Vol-{volume_number}/papers",
                    [dataclasses.asdict(paper) for paper in vol_papers],
                )
        return papers

    def get_ceur_volume_papers(self, volume_number: int) -> List[DblpPaper]:
        """
        Get all papers published in CEUR-WS from dblp
        """
        cache_name = f"dblp/Vol-{volume_number}/papers"
        lod = self.cache_manager.load(cache_name)
        if lod is None:
            all_papers = self.get_all_ceur_papers()
            papers = [
                paper for paper in all_papers if paper.volume_number == volume_number
            ]
            self.cache_manager.store(
                f"dblp/Vol-{volume_number}/papers",
                [dataclasses.asdict(paper) for paper in papers],
            )
        else:
            papers = [DblpPaper(**d) for d in lod]
        return papers

    def getDblpIdByVolumeNumber(self, number) -> List[str]:
        """
        Get the dblp entity id by given volume number
        Args:
            number: volume number
        """
        query = f"""PREFIX dblp: <https://dblp.org/rdf/schema#>
            SELECT *
            WHERE {{ 
                ?proceeding dblp:publishedIn "CEUR Workshop Proceedings";
                            dblp:publishedInSeriesVolume "{number}".
                }}
        """
        try:
            qres = self.sparql.queryAsListOfDicts(query)
        except HTTPError as ex:
            print("dblp sparql endpoint unavailable")
            qres = None
        qIds = []
        if qres is not None and qres != []:
            qIds = [
                record.get("proceeding")[len(self.DBLP_REC_PREFIX) :] for record in qres
            ]
        return qIds

    def get_all_ceur_proceedings(
        self, force_query: bool = False
    ) -> List[DblpProceeding]:
        """
        Get all proceedings published in CEUR-WS from dblp

        Args:
            force_query(bool): if True force query

        """
        dblp_volumes=DblpVolumes(endpoint=self)
        lod=dblp_volumes.load(force_query)
        volumes = []
        editors = self.get_all_ceur_editors(force_query=force_query)
        editorsById = {a.dblp_author_id: a for a in editors}
        papers = self.get_all_ceur_papers(force_query=force_query)
        papersByProceeding = {
            key: list(group)
            for key, group in groupby(
                    papers, lambda paper: paper.dblp_proceeding_id
            )
        }
        for d in lod:
            if int(d.get("volume_number")) == 3000:
                pass
            vol_editors = []
            editor_str = d.get("editor", "")
            # >;<  qlever quirk until 2023-12
            if ">;<" in editor_str:
                delim = ">;<"
            else:
                delim = ";"
            for dblp_author_id in editor_str.split(delim):
                editor = editorsById.get(dblp_author_id, None)
                if editor:
                    vol_editors.append(editor)
            volume = DblpProceeding(
                dblp_publication_id=d.get("proceeding"),
                volume_number=int(d.get("volume_number")),
                dblp_event_id=d.get("dblp_event_id"),
                title=d.get("title"),
                editors=vol_editors,
                papers=papersByProceeding.get(d.get("proceeding")),
            )
            volumes.append(volume)
            self.cache_manager.store(
                dblp_volumes.cache_name, [dataclasses.asdict(volume) for volume in volumes]
            )
            volume_by_number, _errors = LOD.getLookup(volumes, "volume_number")
            for number, volume in volume_by_number.items():
                self.cache_manager.store(
                    f"dblp/Vol-{number}/metadata", volume
                )
        return volumes

    def get_ceur_proceeding(self, volume_number: int) -> DblpProceeding:
        """
        get ceur proceeding by volume number from dblp
        Args:
            volume_number: number of the volume
        """
        cache_name = f"dblp/Vol-{volume_number}/metadata"
        volume = self.cache_manager.load(cache_name,cls=DblpProceeding)
        if volume is None:
            raise ValueError(f"Volume {volume_number} metadata not found in cache") 
        return volume

    def getDblpUrlByDblpId(self, entityId) -> Union[str, None]:
        """
        Get the dblp url for given entity id
        Args:
            entityId: volume url
        """
        if entityId is None or entityId == "":
            return None
        entityUrl = self.DBLP_REC_PREFIX + entityId
        query = f"""PREFIX dblp: <https://dblp.org/rdf/schema#>
                SELECT *
                WHERE {{ 
                    <{entityUrl}> dblp:listedOnTocPage ?url .
                    }}
            """
        qres = self.sparql.queryAsListOfDicts(query)
        qIds = []
        if qres is not None and qres != []:
            qIds = [record.get("url")[len(self.DBLP_EVENT_PREFIX) :] for record in qres]
        qId = qIds[0] if qIds is not None and len(qIds) > 0 else None
        return qId

    def convertEntityIdToUrlId(self, entityId: str) -> Union[str, None]:
        """
        Convert the given entityId to the id used in the url
        Note: use with care this conversion does not always work
        Args:
            entityId: id of the entity
        Example:
            conf/aaai/2022 → conf/aaai/aaai2022

        Returns
            str - id used in the url
            None - if the given entityId can not be converted
        """
        return self.getDblpUrlByDblpId(entityId)

    def toDblpUrl(self, entityId: str, withPostfix: bool = False) -> Union[str, None]:
        """
        Convert the given id to the corresponding dblp url
        Args:
            entityId: dblp event id
            withPostfix: If True add the postfix ".html"

        Returns:
            ddblp url of None if the url can not be generated for the given input
        """
        urlId = self.convertEntityIdToUrlId(entityId)
        if urlId is None:
            return None
        postfix = ".html"
        url = self.DBLP_EVENT_PREFIX + urlId
        if withPostfix:
            url += postfix
        return url

    def getEditorsOfVolume(self, number: Union[int, str, None]) -> List[dict]:
        """
        Get the editors for the given volume number
        Args:
            number: number of the volume if none query for all ceur-ws editors

        Returns:
            list of dictionaries where a dict represents one editor containing all identifiers of the editor
        """
        if number is None:
            number_var = "?volumeNumber"
        else:
            number_var = f'"{number}"'
        dblp_identifiers = DblpAuthorIdentifier.all()
        optional_clauses: List[str] = []
        id_vars: List[str] = []
        for identifier in dblp_identifiers:
            id_var = f"?{identifier.name}"
            optional_clauses.append(
                f"""OPTIONAL{{
                ?editor datacite:hasIdentifier {id_var}_blank.
                {id_var}_blank datacite:usesIdentifierScheme {identifier.dblp_property};
                litre:hasLiteralValue {id_var}Var.}}"""
            )
            id_vars.append(id_var)
        id_selects = "\n".join(
            [
                f"(group_concat(DISTINCT {id_var}Var;separator='|') as {id_var})"
                for id_var in id_vars
            ]
        )
        id_queries = "\n".join(optional_clauses)
        query = f"""PREFIX datacite: <http://purl.org/spar/datacite/>
                    PREFIX dblp: <https://dblp.org/rdf/schema#>
                    PREFIX litre: <http://purl.org/spar/literal/>
                    SELECT DISTINCT (group_concat(DISTINCT ?nameVar;separator='|') as ?name) 
                                    (group_concat(DISTINCT ?homepageVar;separator='|') as ?homepage)
                                    (group_concat(DISTINCT ?affiliationVar;separator='|') as ?affiliation)
                                    {id_selects}
                    WHERE{{
                        ?proceeding dblp:publishedIn "CEUR Workshop Proceedings";
                                    dblp:publishedInSeriesVolume {number_var};
                                    dblp:editedBy ?editor.
                        ?editor dblp:primaryCreatorName ?nameVar.
                        OPTIONAL{{?editor dblp:primaryHomepage ?homepageVar.}}
                        OPTIONAL{{?editor dblp:primaryAffiliation ?affiliationVar.}}
                        {id_queries}
                    }}
                    GROUP BY ?editor
                """
        qres = self.sparql.queryAsListOfDicts(query)
        for record in qres:
            for key, value in record.items():
                if "|" in value:
                    record[key] = value.split(
                        '"|"'
                    )  # issue in qlever see https://github.com/ad-freiburg/qlever/discussions/806
        return qres


@dataclass
class DblpAuthorIdentifier:
    """
    represents an author id available in dblp
    and the corresponding property in wikidata
    """

    name: str  # the name should be usable as SPARQL variable
    dblp_property: str
    wikidata_property: str

    @classmethod
    def all(cls) -> List["DblpAuthorIdentifier"]:
        """
        returns all available identifiers
        """
        res = [
            DblpAuthorIdentifier("dblp", "datacite:dblp", "P2456"),
            DblpAuthorIdentifier("wikidata", "datacite:wikidata", None),
            DblpAuthorIdentifier("orcid", "datacite:orcid", "P496"),
            DblpAuthorIdentifier("googleScholar", "datacite:google-scholar", "P1960"),
            DblpAuthorIdentifier("acm", "datacite:acm", "P864"),
            DblpAuthorIdentifier("twitter", "datacite:twitter", "P2002"),
            DblpAuthorIdentifier("github", "datacite:github", "P2037"),
            DblpAuthorIdentifier("viaf", "datacite:viaf", "P214"),
            DblpAuthorIdentifier("scigraph", "datacite:scigraph", "P10861"),
            DblpAuthorIdentifier("zbmath", "datacite:zbmath", "P1556"),
            DblpAuthorIdentifier("researchGate", "datacite:research-gate", "P6023"),
            DblpAuthorIdentifier("mathGenealogy", "datacite:math-genealogy", "P549"),
            DblpAuthorIdentifier("loc", "datacite:loc", "P244"),
            DblpAuthorIdentifier("linkedin", "datacite:linkedin", "P6634"),
            DblpAuthorIdentifier("lattes", "datacite:lattes", "P1007"),
            DblpAuthorIdentifier("isni", "datacite:isni", "P213"),
            DblpAuthorIdentifier("ieee", "datacite:ieee", "P6479"),
            DblpAuthorIdentifier("gepris", "datacite:gepris", "P4872"),
            DblpAuthorIdentifier("gnd", "datacite:gnd", "P227"),
        ]
        return res

    @classmethod
    def getAllAsMap(cls) -> Dict[str, "DblpAuthorIdentifier"]:
        """
        return all all available identifiers as map
        """
        res = dict()
        for identifier in cls.all():
            res[identifier.name] = identifier
        return res

    @classmethod
    def getWikidataIdQueryPart(cls, id_name: str, value: str, var: str):
        """
        Generates for the given identifier the wikidata query
        Args:
            id_name: name of the identifier
            value: the identifier value
            var: name of the variable which should have the id
        """
        if not var.startswith("?"):
            var = "?" + var
        query = None
        wd_prop = cls.getAllAsMap().get(id_name).wikidata_property
        if id_name == "wikidata":
            values = value
            if isinstance(value, str):
                values = [value]
            value_urls = " ".join([f"wd:{value}" for value in values])
            query = f"""{{ SELECT * WHERE {{ VALUES ?person {{ {value_urls} }} }} }}# {id_name}"""
        elif id_name in cls.getAllAsMap():
            if isinstance(value, list):
                values = " ".join([f'"{value}"' for value in value])
                query = f"""{{OPTIONAL{{
                            VALUES ?{id_name} {{ {values} }}
                            {var} wdt:{wd_prop} ?{id_name}.}} 
                            }}  # {id_name}"""
            else:
                query = f"""{{ {var} wdt:{wd_prop} "{value}". }}  # {id_name}"""
        else:
            pass
        return query
