from transformers import AutoTokenizer, AutoModelForTokenClassification, MarianTokenizer, MarianMTModel
from transformers import pipeline
from typing import Any, List, Dict, Union
import torch
from tqdm import tqdm
from src.get_polygons import _match_locations_to_maps_data
import os
from langdetect import detect
import gc


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

def _get_device():
    if torch.cuda.is_available():
        return "cuda"
    # elif torch.backends.mps.is_available():
    #     return "mps"
    else:
        return "cpu"

class GeolocationExtractor:
    def __init__(
        self,
        model_name: str = os.getenv(
            "NER_MODEL_NAME", "dbmdz/bert-large-cased-finetuned-conll03-english"
        ),
        translate_to_english: bool = True,
        mt_to_en_model: str = os.getenv(
            "MT_TO_EN_MODEL_NAME", "Helsinki-NLP/opus-mt-mul-en"
        ),
    ):

        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForTokenClassification.from_pretrained(model_name)
        self.device = _get_device()
        self.nlp_ner = pipeline(
            "ner",
            model=model,
            tokenizer=tokenizer,
            grouped_entities=True,
            device=self.device,
        )
        self.do_translation = translate_to_english
        if self.do_translation:
            self.mt_to_en_tokenizer = MarianTokenizer.from_pretrained(mt_to_en_model)
            self.mt_to_en_model = MarianMTModel.from_pretrained(mt_to_en_model)
            self.mt_to_en_model.to(self.device)

    @torch.no_grad()
    def _translate_loc_to_english(
        self, text: List[str], batch_size: int = 8
    ) -> List[str]:

        translations = []
        for i in tqdm(
            range(0, len(text), batch_size),
            desc="Translating locations to english",
        ):
            batch = text[i : i + batch_size]
            encoded = self.mt_to_en_tokenizer(batch, return_tensors="pt").to(self.device)
            # Move inputs to CPU for MPS compatibility if needed
            if self.device == "mps":
                encoded = {k: v.cpu() for k,v in encoded.items()}
                translated = self.mt_to_en_model.generate(**encoded)
            else:
                translated = self.mt_to_en_model.generate(**encoded)
            translations.extend(
                [self.mt_to_en_tokenizer.decode(t, skip_special_tokens=True) for t in translated]
            )
            gc.collect()
        return translations

    @torch.no_grad()
    def extract_locations(
        self, text: List[str], batch_size: int = 32
    ) -> List[Dict[str, str]]:
        ner_results = []
        for i in tqdm(range(0, len(text), batch_size), desc="Extracting locations"):
            batch = text[i : i + batch_size]
            batch_results = self.nlp_ner(batch)

            gc.collect()

            # Flatten and filter locations
            for entry_results in batch_results:
                locations = [
                    {"original": entity["word"]}
                    for entity in entry_results
                    if entity["entity_group"] == "LOC"
                ]
                ner_results.append(locations)

        return ner_results

    @torch.no_grad()
    def _do_translations(
        self, ner_results: List[Dict[str, str]], batch_size: int = 8
    ) -> List[List[str]]:

        translations = []
        original_location_ids = [[] for _ in range(len(ner_results))]
        original_location_languages = [[] for _ in range(len(ner_results))]
        locations_count = 0

        to_be_translated = []
        to_be_translated_ids = []

        for i, original_locations in enumerate(ner_results):
            for j, one_location in enumerate(original_locations):
                try:
                    language = detect(one_location["original"])
                except:
                    language = "-"
                original_location_languages[i].append(language)
                original_location_ids[i].append(locations_count)

                if language != "en":
                    to_be_translated.append(one_location["original"])
                    to_be_translated_ids.append(locations_count)

                locations_count += 1

        translations_list: List[str] = self._translate_loc_to_english(
            to_be_translated, batch_size
        )

        # after doing the translations, i need to return a list of lists
        # where each sublist contains the translations for the locations if they are not english
        # or the locations themselve if they are english

        translated_locations = []
        locations_index = 0
        for i, original_locations in enumerate(ner_results):
            translated_sublist = []
            for j, one_location in enumerate(original_locations):
                if original_location_languages[i][j] == "en":
                    final_translation = one_location["original"]
                else:
                    final_translation = translations_list[locations_index]
                    locations_index += 1
                
                translated_sublist.append(final_translation)
            translated_locations.append(translated_sublist)

        return translated_locations

    def __call__(self, text: List[str], countries: List[str]) -> Dict[str, List[Any]]:
        # process all entries with batches

        ner_results: List[Dict[str, str]] = self.extract_locations(text)

        if self.do_translation:
            translations: List[List[str]] = self._do_translations(ner_results)
            for i, one_entry_translations in enumerate(translations):
                for j, one_translation in enumerate(one_entry_translations):
                    ner_results[i][j]["translated_to_en"] = one_translation

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
