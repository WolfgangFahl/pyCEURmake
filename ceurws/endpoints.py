"""
SPARQL endpoint configurations for CEUR-WS

This module provides access to SPARQL endpoints for querying Wikidata and DBLP.
Endpoints are now configured via YAML files for better maintainability.

Created on 2024-02-11
Updated to use YAML-based endpoint configuration from pyLoDStorage

@author: wf
"""
from pathlib import Path
from lodstorage.query import EndpointManager

# Get the resources directory
RESOURCES_DIR = Path(__file__).parent / "resources"
ENDPOINTS_YAML = RESOURCES_DIR / "endpoints.yaml"

# Load endpoints from YAML
if ENDPOINTS_YAML.exists():
    _endpoint_manager = EndpointManager.of_yaml(str(ENDPOINTS_YAML))
    WIKIDATA_ENDPOINT = _endpoint_manager.get_endpoint("wikidata")
    DBLP_ENDPOINT = _endpoint_manager.get_endpoint("dblp")
else:
    raise Exception(f"{ENDPOINTS_YAML} missing")


