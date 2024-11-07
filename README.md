# Geolocations and Polygons Extraction Package

## Overview

This package is designed to extract geographical locations and their corresponding administrative-level polygons from textual data. It processes multilingual inputs, identifies geolocations mentioned in the text, and retrieves detailed metadata at various administrative levels.

## Installation

To install the package, use the following command:

```bash
git clone https://github.com/MediaMonitoringAndAnalysis/geo_extract.git
cd geo_extract
```

## Dataset Creation

To create the dataset for geolocation extraction, we use the `fieldmaps` polygons dataset. Follow the steps below to prepare the dataset.

### Steps:

1. **Download the Polygons Dataset:**

   Go to the [Fieldmaps website](https://fieldmaps.io/data) and download the `adm4_polygons.gpkg` file.

2. **Place the File:**

   Move the downloaded `adm4_polygons.gpkg` file into the following folder in your project:

   ```bash
   cd data/dataprep/
   ```
   
3. **Run the Script:**

    To process the polygons data, run the following script:

    ```bash
    python load_gpkg_polygons_data.py
    ```
    This script will load the polygons data and prepare it for use in the geolocation extraction process.

## Usage

Here’s an example of how to use the package with a sample input and the expected output.

### Input structure
- **text** (`list of str`): A list of textual data containing potential mentions of geographical locations.
- **countries** (`list of str`): A list of country names to help narrow down the possible geolocations within the text.

### Output structure
- **geolocations** (`list of list`): A list where each element corresponds to a sentence in the input text. Each sublist contains dictionaries representing identified locations, with the original text and its English translation.
- **geolocation_by_admin_level** (`list of dict`): This dictionary maps geolocations to their corresponding administrative levels. The key is the location name, and the value is a dictionary containing information for each administrative level (e.g., country, region).
- **location_by_adm_level_X** (`list of list`): For each administrative level (adm_level_0 to adm_level_4), this contains the location information extracted at that level for each sentence. This data includes the location ID, name, and Pcode.


### Example Usage

```python
from typing import List

text: List[str] = ["Je suis en Tunisie", "I am in Nabeul", "I am nowhere"]
countries: List[str] = ["Tunisia"]

from main_geolocations_extractor import extract_geolocations
outputs = extract_geolocations(text, countries)
```

#### Example Output

```python
outputs = {
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
```