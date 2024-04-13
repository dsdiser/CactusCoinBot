import logging
import random
from typing import Any, Dict
from openfoodfacts import API
from openfoodfacts.types import COUNTRY_CODE_TO_NAME
from functools import lru_cache

from src.models import CountryAnswer, Food, database

USER_AGENT = "CactusCoinBot/1.0"
MAX_NUM_WRONG_ANSWERS = 3
TOTAL_NUM_ANSWERS = 4



@lru_cache(maxsize=50)
def format_country(country: str) -> str:
    # formats string like "en:united-states" to "United States"
    country_formatted = country[3:]
    country_words = [word.capitalize() for word in country_formatted.split('-')]
    return " ".join(country_words)


def generate_food_questions():
    # Come up with a randomized list of 20 counties
    country_codes = random.choices(list(COUNTRY_CODE_TO_NAME.keys()), k=20)
    rows_inserted = 0
    # Get food items for each of them
    for country_code in country_codes:
        # pull 20 products
        try:
            logging.debug("pulling country")
            new_products: list[Dict[str, Any]] = []
            new_countries = []
            correct_countries: list[list[str]] = []
            api = API(user_agent="CactusCoinBot/1.0", country=country_code)
            results = api.product.text_search("", sort_by="last_modified_t")
            assert results, "must have results from the search"
            products = results["products"]
            all_countries = set()
            for product in products:
                countries = product.get("countries_tags", None)
                product_name = product.get("product_name_en", None)
                image_url = product.get("image_url", None)
                barcode_id = product.get("id", None)
                if not countries or not product_name or not image_url or not barcode_id:
                    continue
                all_countries.update(countries)
                # create list of objects to insert into DB
                correct_countries.append(countries)
                new_products.append({"name": product_name, "image_url": image_url, "barcode": barcode_id, "used": False})

            if not new_products:
                continue

            # if we don't have enough fake answers, add some new fake answers
            if len(all_countries) < 3:
                all_unused_countries = set(COUNTRY_CODE_TO_NAME.values()) - all_countries
                all_countries.update(random.sample(all_unused_countries, k=5))

            for idx, product in enumerate(new_products):
                # Create set of countries that could be used for wrong answers
                correct_countries_src = correct_countries[idx]
                wrong_countries = all_countries.copy().difference(correct_countries_src)
                needed_num_wrong_answers = TOTAL_NUM_ANSWERS - len(correct_countries_src)

                num_wrong_answers = random.randint(needed_num_wrong_answers, MAX_NUM_WRONG_ANSWERS)
                wrong_answers = random.sample(wrong_countries, k=num_wrong_answers)
                correct_answers = random.sample(correct_countries_src, k=TOTAL_NUM_ANSWERS-num_wrong_answers)
                # convert country tag to generic english
                wrong_answer_set = [format_country(country) for country in wrong_answers]
                correct_answer_set = [format_country(country) for country in correct_answers]
                # add countries to database
                wrong_countries_to_insert = [{"barcode": product["barcode"], "correct": False, "name": country_name} for country_name in wrong_answer_set]
                correct_countries_to_insert = [{"barcode": product["barcode"], "correct": True, "name": country_name} for country_name in correct_answer_set]
                new_countries += wrong_countries_to_insert + correct_countries_to_insert
            
            # Make this a transaction so everything needs to be inserted at once
            logging.debug("about to send to db")
            with database.atomic() as txn:
                rows_inserted += Food.insert_many(new_products).execute()
                CountryAnswer.insert_many(new_countries).execute()
        except Exception as e:
            logging.error(e)
    logging.info(f"{str(rows_inserted)} rows inserted.")
