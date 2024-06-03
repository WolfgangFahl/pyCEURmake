"""
Created on 2021-08-19

@author: wf
"""

import getpass
import os
import socket
import time
from unittest import TestCase

#import pytest
import requests
from lodstorage.query import Endpoint
from lodstorage.sparql import SPARQL

from ceurws.services.entity_fishing import ENTITY_FISHING_ENDPOINT


class Basetest(TestCase):
    """
    base test case
    """

    def setUp(self, debug=False, profile=True):
        """
        setUp test environment
        """
        TestCase.setUp(self)
        self.debug = debug
        self.profile = profile
        msg = f"test {self._testMethodName}, debug={self.debug}"
        self.profiler = Profiler(msg, profile=self.profile)

    def tearDown(self):
        TestCase.tearDown(self)
        self.profiler.time()

    @staticmethod
    def inPublicCI():
        """
        are we running in a public Continuous Integration Environment?
        """
        publicCI = getpass.getuser() in ["travis", "runner"]
        jenkins = "JENKINS_HOME" in os.environ
        return publicCI or jenkins


class Profiler:
    """
    simple profiler
    """

    def __init__(self, msg, profile=True):
        """
        construct me with the given msg and profile active flag

        Args:
            msg(str): the message to show if profiling is active
            profile(bool): True if messages should be shown
        """
        self.msg = msg
        self.profile = profile
        self.starttime = time.time()
        if profile:
            print(f"Starting {msg} ...")

    def time(self, extraMsg=""):
        """
        time the action and print if profile is active
        """
        elapsed = time.time() - self.starttime
        if self.profile:
            print(f"{self.msg}{extraMsg} took {elapsed:5.1f} s")
        return elapsed


def _requires_neo4j():
    """
    test case requires local neo4j instance
    """
    has_neo4j = False
    try:
        port = 7474
        host = socket.gethostbyname(socket.gethostname())
        url = f"http://{host}:{port}"
        requests.get(url)
        has_neo4j = True
    except requests.exceptions.ConnectionError:
        pass
    return pytest.mark.skipif(not has_neo4j, reason="neo4j instance is required")


requires_neo4j = _requires_neo4j()


def requires_sparql_endpoint(*, endpoint: Endpoint):
    """
    test case requires given SPARQL endpoint
    """
    is_unavailable = True
    sparql = SPARQL(endpoint.endpoint, method=endpoint.method)
    availability_query = "SELECT * WHERE {}"
    try:
        sparql.query(availability_query)
        is_unavailable = False
    except Exception as e:
        print(e)
    return pytest.mark.skipif(is_unavailable, reason=f" SPARQL endpoint {endpoint.name} is unavailable")


def _requires_entity_fishing_endpoint():
    """
    test case requires entity fishing endpoint
    """
    is_unavailable = True
    try:
        url = f"{ENTITY_FISHING_ENDPOINT}/service/kb/concept/Q5"
        resp = requests.get(url)
        resp.raise_for_status()
        is_unavailable = False
    except Exception as e:
        print(e)
    return pytest.mark.skipif(is_unavailable, reason="entity fishing endpoint is not available")


requires_entity_fishing_endpoint = _requires_entity_fishing_endpoint()
