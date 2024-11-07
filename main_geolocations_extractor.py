from typing import List
from src.geolocation_extraction import GeolocationExtractor


def extract_geolocations(text: List[str], countries: List[str]) -> dict:
    """
    output: {
        "extracted_locations": All raw extracted_geolocations,
        "matched_locations": matched_locations,
        "location_by_adm_level": location_by_adm_level,
    }

    Example input:
    "text": ["Je suis en Tunisie", "I am in Nabeul", "I am nowhere"]
    "countries": ["Tunisia"]

    Example output:
    output = {
        "geolocations": [
            [{"original": "Tunisie", "translated_to_en": "Tunisia"}],
            [{"original": "Nabeul", "translated_to_en": "Nabeul"}],
            [],
        ],
        "geolocation_by_admin_level": [
            {"Tunisie": {0: {"id": "TUN-20240327", "name": "Tunisia", "Pcode": "TUN"}}},
            {
                "Nabeul": {
                    1: {
                        "id": "TUN-20230119-16",
                        "name": "Nabeul",
                        "Pcode": "13205935B21712567795690",
                    },
                    0: {"id": "TUN-20240327", "name": "Tunisia", "Pcode": "TUN"},
                }
            },
            {},
        ],
        "location_by_adm_level_0": [
            [{"id": "TUN-20240327", "name": "Tunisia", "Pcode": "TUN"}],
            [{"id": "TUN-20240327", "name": "Tunisia", "Pcode": "TUN"}],
            [],
        ],
        "location_by_adm_level_1": [
            [],
            [
                {
                    "id": "TUN-20230119-16",
                    "name": "Nabeul",
                    "Pcode": "13205935B21712567795690",
                }
            ],
            [],
        ],
        "location_by_adm_level_2": [[], [], []],
        "location_by_adm_level_3": [[], [], []],
        "location_by_adm_level_4": [[], [], []],
    }
    """
    extractor = GeolocationExtractor()
    
    outputs = extractor(text, countries=countries)

    return outputs

