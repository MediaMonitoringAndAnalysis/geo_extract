from transformers import AutoTokenizer, AutoModelForTokenClassification
from transformers import pipeline
from typing import Any, List, Dict, Union
import torch
from tqdm import tqdm
from src.get_polygons import _match_locations_to_maps_data
import os
from langdetect import detect


def _get_adm_n_locations(
    one_entry_extracted_locations: List[Dict[str, Dict[int, Dict[str, str]]]],
    adm_level: int,
) -> List[str]:
    adm_n_locations = []
    addded_location_ids = set()

    for extracted_loc_name, extracted_loc_data in one_entry_extracted_locations.items():
        if (
            adm_level in extracted_loc_data
            and extracted_loc_data[adm_level]["id"] not in addded_location_ids
        ):
            adm_n_locations.append(extracted_loc_data[adm_level])
            addded_location_ids.add(extracted_loc_data[adm_level]["id"])
    return adm_n_locations


class GeolocationExtractor:
    def __init__(
        self,
        model_name: str = os.getenv(
            "NER_MODEL_NAME", "dbmdz/bert-large-cased-finetuned-conll03-english"
        ),
        translate_to_english: bool = True,
        mul_to_en_model: str = os.getenv(
            "ES_TO_EN_MODEL_NAME", "Helsinki-NLP/opus-mt-mul-en"
        ),
    ):

        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForTokenClassification.from_pretrained(model_name)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.nlp = pipeline(
            "ner",
            model=model,
            tokenizer=tokenizer,
            grouped_entities=True,
            device=self.device,
        )
        self.do_translation = translate_to_english
        if self.do_translation:
            self.mul_to_en_model = pipeline("translation", model=mul_to_en_model)

    def _translate_loc_to_english(self, text: str) -> str:
        language = detect(text)
        if language == "en":
            translated_entry = text
        else:
            translated_entry = self.mul_to_en_model(text)[0]["translation_text"]

        return translated_entry

    def _process_one_entry(self, textual_entry: str) -> List[Dict[str, str]]:

        ner_results = self.nlp(textual_entry)
        # keep only locations
        ner_results = [
            {"original": entity["word"]}
            for entity in ner_results
            if entity["entity_group"] == "LOC"
        ]
        if self.do_translation:
            for i, original_loc in enumerate(ner_results):
                translated_loc = self._translate_loc_to_english(
                    original_loc["original"]
                )
                ner_results[i]["translated_to_en"] = translated_loc

        return ner_results

    def __call__(self, text: List[str], countries: List[str]) -> Dict[str, List[Any]]:
        # process all entries with batches

        ner_results = []
        for entry in tqdm(text, desc="Extracting geolocations"):
            ner_results.append(self._process_one_entry(entry))

        matched_locations = _match_locations_to_maps_data(ner_results, countries)

        outputs = {
            "geolocations": ner_results,
            "geolocation_by_admin_level": matched_locations,
        }

        for admin_lvl in range(5):
            adm_n_locations = [
                _get_adm_n_locations(matched_locations_one_entry, admin_lvl)
                for matched_locations_one_entry in matched_locations
            ]
            outputs[f"location_by_adm_level_{admin_lvl}"] = adm_n_locations

        return outputs
