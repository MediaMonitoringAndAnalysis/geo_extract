import os
from typing import List, Dict, Set, Any
from fuzzywuzzy import fuzz
import json


countries_mapping = {
    "DPRK": ["Democratic People's Republic of Korea"],
    "Russia": ["Russian Federation"],
    "DRC": ["Democratic Republic of the Congo"],
    "Timor Leste": ["Timor-Leste"],
    "Venezuela": ["Venezuela (Bolivarian Republic of)"],
    "Moldova": ["Republic of Moldova"],
    "Tanzania": ["United Republic of Tanzania"],
    "Palestine": ["Gaza", "West Bank"],
    "occupied Palestinian territory": ["Gaza", "West Bank"],
    "Armenia,Azerbaijan": ["Armenia", "Azerbaijan"],
    "CAR": ["Central African Republic"],
    "Laos": ["Lao People's Democratic Republic"],
    "Iran": ["Iran (Islamic Republic of)"],
    "Syria": ["Syrian Arab Republic"],
    "Czech Republic": ["Czechia"],
}


def _map_offcial_name_to_mapped_name(country: str):

    if country in countries_mapping:
        return countries_mapping[country]
    return [country]


def _flatten_lists(list_of_lists: List[List[Any]]) -> List[Any]:
    return [item for sublist in list_of_lists for item in sublist]


def _find_matches(
    input_terms: List[str],
    geo_names: List[str],
    similaritty_threshold=95,
    length_threshold=0.7,
) -> List[Dict[str, int]]:
    """
    Find matches for one term
    """

    # Try exact match
    for one_inpt_term in input_terms:
        if one_inpt_term in geo_names:
            return [one_inpt_term]

    matches = []
    # Try partial matches
    for one_input_term in input_terms:
        no_spaces_input_term = one_input_term.replace(" ", "")
        for key in geo_names:
            similarity_score = fuzz.partial_ratio(
                no_spaces_input_term, key.replace(" ", "")
            )

            if similarity_score >= similaritty_threshold and abs(
                len(key) - len(one_input_term)
            ) <= length_threshold * min(len(key), len(one_input_term)):
                matches.append({"match": key, "score": similarity_score})
                
    #TODO: add AI-based matching

    # keep matches with the highest score
    matches = sorted(matches, key=lambda x: x["score"], reverse=True)
    matches = [matches[0]["match"]] if len(matches) > 0 else []

    return matches


# def _admin1_available_countries():
#     available_countries_list = set()
#     file_path = os.path.join("..", "polygons_data", "adm1_polygons.gpkg")
#     with fiona.open(
#         file_path, vfs="{}".format(file_path), enabled_drivers="GeoJSON"
#     ) as src:
#         for feature in src:
#             # Check if the feature satisfies the SQL filter condition for rows
#             available_countries_list.add(feature["properties"]["adm0_name"])

#     available_countries_list = list(available_countries_list)
#     return available_countries_list


def _get_final_location_ids(
    extracted_geolocation: List[List[str]],
    feature_names_to_id: Dict[str, Dict[str, Dict[str, str]]],
) -> List[Dict[str, Dict[str, Dict[str, str]]]]:

    final_locations = []
    for geolocations_one_extract in extracted_geolocation:
        matched_locations_one_extract = {}
        for locs in geolocations_one_extract:
            # locs contains original location and translated loc

            matched_locations = _find_matches(
                list(locs.values()), list(feature_names_to_id.keys())
            )

            if len(matched_locations) == 0:
                final_locations_one_loc = {}

            else:
                one_loc = matched_locations[0]  # only one location is there

                final_locations_one_loc = {}

                # try:
                # print(feature_names_to_id[one_loc])
                extracted_location = {
                    "id": feature_names_to_id[one_loc]["id"],
                    "name": one_loc,
                    "Pcode": feature_names_to_id[one_loc]["Pcode"],
                }

                final_locations_one_loc[feature_names_to_id[one_loc]["admin_level"]] = (
                    extracted_location
                )

                parent_locations = feature_names_to_id[one_loc]["parent_locations"]
                for parent_loc_id, one_parent_properties in parent_locations.items():

                    admin_level = int(parent_loc_id.split(" ")[1])

                    loc_name = one_parent_properties["name"]
                    loc_props = {
                        "id": feature_names_to_id[loc_name]["id"],
                        "name": loc_name,
                        "Pcode": feature_names_to_id[loc_name]["Pcode"],
                    }

                    final_locations_one_loc[admin_level] = loc_props

            matched_locations_one_extract[locs["original"]] = final_locations_one_loc
        final_locations.append(matched_locations_one_extract)

    return final_locations


def _get_geolocations_by_admin_level(
    all_rows_locations: List[Dict[str, Dict[str, Dict[str, str]]]],
    location_names_to_id: Dict[str, Dict[str, Dict[str, str]]],
):
    final_locations_data = []
    for one_extract_locations in all_rows_locations:
        locations_by_admin_level = {adm_level: set() for adm_level in range(0, 5)}
        for original_loc_name, loc_values in one_extract_locations.items():
            for _, location_ids in loc_values.items():
                one_loc_name = location_ids["name"]
                location_admin_level = location_names_to_id[one_loc_name]["admin_level"]
                locations_by_admin_level[location_admin_level].add(one_loc_name)
        final_locations_data.append(
            {k: list(v) for k, v in locations_by_admin_level.items()}
        )

    final_locations_data = [
        {k: v[0] for k, v in one_loc_data.items() if len(v) > 0}
        for one_loc_data in final_locations_data
    ]

    return final_locations_data


def _match_locations_to_maps_data(
    extracted_geolocations: List[List[Dict[str, str]]],
    treated_country_names: List[str],
    feature_names_to_id: os.PathLike = os.path.join("data", "feature_name_to_id.json"),
) -> Dict[str, List[Any]]:

    # if not os.path.exists(saved_geolocations_data_folder):
    mapped_country_names = list(
        set(
            _flatten_lists(
                [
                    _map_offcial_name_to_mapped_name(country_name)
                    for country_name in treated_country_names
                ]
            )
        )
    )

    with open(feature_names_to_id, "r") as f:
        feature_names_to_id = json.load(f)

    country_specific_feature_names_to_id = {}
    for country_name in mapped_country_names:
        if country_name not in feature_names_to_id:
            print(f"Country {country_name} not found in feature_names_to_id")
            continue
        country_specific_feature_names_to_id.update(feature_names_to_id[country_name])

    matched_locations = _get_final_location_ids(
        extracted_geolocations,
        country_specific_feature_names_to_id,
    )

    return matched_locations
