from typing import List, Set, Optional, Dict
import fiona
import geopandas as gpd
from shapely.geometry import mapping, shape
import json
from collections import defaultdict
from tqdm import tqdm
from fuzzywuzzy import fuzz
import pandas as pd
import os
from copy import copy


def _create_filtered_features(file_path: os.PathLike, highest_polygon_id: int):
    if not os.path.exists(file_path):
        return {}
    feature_name_to_id = defaultdict(lambda: defaultdict(dict))

    with fiona.open(
        file_path, vfs="{}".format(file_path), enabled_drivers="GeoJSON"
    ) as src:
        with tqdm(
            total=len(src),
            desc=f"Processing features {file_path.split('/')[-1].replace('.gpkg', '')}",
        ) as pbar:

            for feature in src:
                country_name = feature["properties"]["adm0_name"]
                # Check if the feature satisfies the SQL filter condition for rows
                # if country_name in countries:
                # print(f"Processing {country_name}")
                for child_level_id in range(0, highest_polygon_id + 1):

                    child_level_name = f"adm{child_level_id}_name"
                    # if child_level_id == 4:
                    #     for property in feature["properties"]:
                    #         if property.startswith("adm"):
                    #             print(
                    #                 "feature name:",
                    #                 property,
                    #                 ", ---feature value:",
                    #                 feature["properties"][property],
                    #             )

                    if feature["properties"][child_level_name] is not None:

                        parent_locations = {
                            f"parent {i}": {
                                "name": feature["properties"][f"adm{i}_name{name_id}"],
                                "id": feature["properties"][f"adm{i}_id"],
                            }
                            for i in range(0, child_level_id)
                            for name_id in ["", "1", 2]
                            if feature["properties"][f"adm{i}_name{name_id}"]
                            is not None
                        }

                        geo_id = feature["properties"][f"adm{child_level_id}_id"]
                        geo_names = []
                        for name_id in ["", 1, 2]:
                            geo_one_name = feature["properties"][
                                f"adm{child_level_id}_name{name_id}"
                            ]
                            if geo_one_name is not None:
                                geo_names.append(geo_one_name)

                        feature_pcode = feature["properties"][
                            f"adm{child_level_id}_src"
                        ]

                        for geo_name in geo_names:
                            feature_name_to_id[country_name][geo_name]["id"] = geo_id
                            feature_name_to_id[country_name][geo_name][
                                "Pcode"
                            ] = feature_pcode
                            feature_name_to_id[country_name][geo_name][
                                "admin_level"
                            ] = child_level_id
                            # if len(parent_locations) > 0:
                            feature_name_to_id[country_name][geo_name][
                                "parent_locations"
                            ] = parent_locations

                pbar.update(1)
    return feature_name_to_id


def _merge_feature_name_to_id_data(
    polygons_feature_name_to_id, points_feature_name_to_id
):
    final_feature_name_to_id = copy(polygons_feature_name_to_id)
    final_feature_name_to_id.update(points_feature_name_to_id)
    return final_feature_name_to_id


def _prepare_gpkg_data(
    relevant_name_part: str,
    feature_name_to_id_file_path: os.PathLike
):  # Not mentioning 'geometry' in imported_columns
    """
    This function loads the polygons from the GeoPackage file and returns a GeoJSON object.
    """

    highest_polygon_id = int(relevant_name_part[-1])

    polygons_data_path = f"{relevant_name_part}_polygons.gpkg"
    polygons_feature_name_to_id = _create_filtered_features(
        polygons_data_path, highest_polygon_id=highest_polygon_id
    )

    points_data_path = f"{relevant_name_part}_points.gpkg"

    points_feature_name_to_id = _create_filtered_features(
        points_data_path, highest_polygon_id=highest_polygon_id
    )

    feature_name_to_id = _merge_feature_name_to_id_data(
        polygons_feature_name_to_id, points_feature_name_to_id
    )

    # save the feature_name_to_id dictionary
    with open(
        feature_name_to_id_file_path,
        "w",
    ) as f:
        json.dump(feature_name_to_id, f, indent=4)


if __name__ == "__main__":
    
    feature_name_to_id_file_path = os.path.join("..", "feature_name_to_id.json")
    if not os.path.exists(feature_name_to_id_file_path):
        _prepare_gpkg_data(
            relevant_name_part="adm4",
            feature_name_to_id_file_path=feature_name_to_id_file_path,
        )
        

    countries_list_path = os.path.join("..", "countries_list.json")
    if not os.path.exists(countries_list_path):
        
        with open("../feature_name_to_id.json", "r") as f:
            feature_name_to_id = json.load(f)
            
        countries_list = list(feature_name_to_id.keys())
        with open(countries_list_path, "w") as f:
            json.dump(countries_list, f, indent=4)