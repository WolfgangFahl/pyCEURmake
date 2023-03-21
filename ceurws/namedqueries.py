'''
Created on 2023-03-21

@author: wf
'''
from wikibot3rd.wikiclient import WikiClient
from wikibot3rd.smw import SMWClient
from lodstorage.query import Query,QueryManager
import yaml
class NamedQueries():
    """
    get named queries
    """
    def __init__(self,wikiId:str="cr"):
        """
        """
        self.wikiId=wikiId
        self.wikiClient=WikiClient.ofWikiId(wikiId)
        if self.wikiClient.needsLogin():
            self.wikiClient.login()
        self.smw=SMWClient(self.wikiClient.getSite())
        self.qm=None
 
    def query(self):
        """
        run query
        """
        ask_query="""
        {{#ask: [[Concept:Query]]
|mainlabel=Query
|?Query id = id
|?Query name=name
|?Query title = title
|?Query tryiturl = tryiturl
|?Query wdqsurl = wdqsurl
|?Query sparql=sparql
|?Query relevance = relevance
|?Query task = task
|limit=200
|sort=Query task,Query id
|order=ascending
}}"""
        self.q_records=self.smw.query(ask_query)
        
    def toQueryManager(self)->QueryManager:
        """
        convert me to a QueryManager
        """
        self.qm=QueryManager(lang="sparql")
        self.qm.queriesByName={}
        for q_record in self.q_records.values():
            name=q_record["name"]
            sparql=q_record["sparql"]
            if name and sparql:
                query=Query(name,query=sparql)
                self.qm.queriesByName[name]=query
        return self.qm
    
    def toYaml(self)->str:
        if self.qm is None:
            self.query()
            self.toQueryManager()
        yaml_str="# named queries\n"
        for query in self.qm.queriesByName.values():
            yaml_str+=f"""'{query.name}':
    sparql: |
"""            
            for line in query.query.split("\n"):
                yaml_str+=f"      {line}\n"
        return yaml_str
        
        
        
        
        
        