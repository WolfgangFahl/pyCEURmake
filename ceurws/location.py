"""
Created on 2023-07-15

@author: wf
"""
import sys

from geograpy.locator import LocationContext
from geograpy.nominatim import NominatimWrapper


class LocationLookup:
    """
    Class for location lookup.
    """

    predefinedLocations = {}

    @classmethod
    def initPredefinedLocations(cls):
        """
        Initialize predefined locations.
        """
        locMap = {
            "Not Known": None,
            "Online": None,
            "Virtual": None,
            "Virtual, USA": None,
            "Virtual Event, USA": None,
            "Amsterdam": "Q727",
            "Amsterdam, Amsterdam": "Q727",
            "Amsterdam Netherlands": "Q727",
            "Amsterdam, Netherlands": "Q727",
            "Amsterdam, The Netherlands": "Q727",
            "Amsterdam The Netherlands": "Q727",
            # ... add more predefined locations ...
        }
        cls.predefinedLocations = locMap

    def __init__(self):
        """
        Constructor for LocationLookup.
        """
        LocationLookup.initPredefinedLocations()
        self.locationContext = LocationContext.fromCache()
        cacheRootDir = LocationContext.getDefaultConfig().cacheRootDir
        cacheDir = f"{cacheRootDir}/.nominatim"
        self.nominatimWrapper = NominatimWrapper(cacheDir=cacheDir)

    def getCityByWikiDataId(self, wikidataID: str):
        """
        Get the city for the given wikidataID.

        Args:
            wikidataID (str): The wikidata ID.

        Returns:
            City: The city with the given wikidataID.
        """
        citiesGen = self.locationContext.cityManager.getLocationsByWikidataId(
            wikidataID
        )
        if citiesGen is not None:
            cities = list(citiesGen)
            if len(cities) > 0:
                return cities[0]
        else:
            return None

    def lookupNominatim(self, locationText: str):
        """
        Lookup the location for the given locationText (if any).

        Args:
            locationText (str): The location text to search for.

        Returns:
            City: The location found by Nominatim.
        """
        location = None
        wikidataId = self.nominatimWrapper.lookupWikiDataId(locationText)
        if wikidataId is not None:
            location = self.getCityByWikiDataId(wikidataId)
        return location

    def lookup(self, locationText: str, logFile=sys.stdout):
        """
        Lookup a location based on the given locationText.

        Args:
            locationText (str): The location to lookup.
            logFile (file): The log file to write the output.

        Returns:
            City: The located city based on the locationText.
        """
        if locationText in LocationLookup.predefinedLocations:
            locationId = LocationLookup.predefinedLocations[locationText]
            if locationId is None:
                return None
            else:
                location = self.getCityByWikiDataId(locationId)
                if location is None:
                    print(
                        f"❌❌-predefinedLocation {locationText}→{locationId} wikidataId not resolved",
                        file=logFile,
                    )
                return location
        lg = self.lookupGeograpy(locationText)
        ln = self.lookupNominatim(locationText)
        if ln is not None and lg is not None and not ln.wikidataid == lg.wikidataid:
            print(f"❌❌{locationText}→{lg}!={ln}", file=logFile)
            return None
        return lg

    def lookupGeograpy(self, locationText: str):
        """
        Lookup the given location by the given locationText.

        Args:
            locationText (str): The location to lookup.

        Returns:
            City: The located city based on the locationText.
        """
        locations = self.locationContext.locateLocation(locationText)
        if len(locations) > 0:
            return locations[0]
        else:
            return None
