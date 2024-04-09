import logging
import random
from typing import Any, Dict
from openfoodfacts import API
from openfoodfacts.types import COUNTRY_CODE_TO_NAME

from src.models import Food

USER_AGENT = "CactusCoinBot/1.0"
MAX_NUM_WRONG_ANSWERS = 3
TOTAL_NUM_ANSWERS = 4


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
            print("pulling country")
            new_products: list[Dict[str, Any]] = []
            api = API(user_agent="CactusCoinBot/1.0", country=country_code)
            results = api.product.text_search("", sort_by="last_modified_t")
            products = results["products"]
            all_countries = set()
            for product in products:
                countries = product.get("countries_tags", None)
                product_name = product.get("product_name_en", None)
                image_url = product.get("image_url", None)
                barcode_id = product.get("id", None)
                if not countries or not product_name or not image_url or not barcode_id:
                    continue
                # create list of objects to insert into DB
                all_countries.update(countries)
                new_products.append({"correct_countries": countries, "name": product_name, "image_url": image_url, "barcode": barcode_id, "used": False})

            # if we don't have enough fake answers, add some new fake answers
            if len(all_countries) < 3:
                all_countries.update(random.sample(list(COUNTRY_CODE_TO_NAME.values()), k=10))

            for idx, product in enumerate(new_products):
                # Create set of countries that could be used for wrong answers
                correct_countries = product["correct_countries"]
                wrong_countries = all_countries.copy().difference(correct_countries)
                needed_num_wrong_answers = TOTAL_NUM_ANSWERS - len(correct_countries)
                # TODO: Deal with if a product doesn't have 4 possible countries
                num_wrong_answers = random.randint(needed_num_wrong_answers, MAX_NUM_WRONG_ANSWERS)
                wrong_answers = random.sample(wrong_countries, k=num_wrong_answers)
                correct_answers = random.sample(correct_countries, k=TOTAL_NUM_ANSWERS-num_wrong_answers)
                # convert country tag to generic english
                answer_set = [format_country(country) for country in wrong_answers + correct_answers]
                correct_answer_set = [format_country(country) for country in correct_countries]
                # need to add to country first
                new_products[idx].update({"countries": answer_set, "correct_countries": correct_answer_set})
            # Insert into DB, ignore any matching barcodes
            print("about to send to db")
            rows_inserted += Food.insert_many(new_products).on_conflict_ignore().execute()
        except Exception as e:
            logging.error(e)
    logging.info(f"{str(rows_inserted)} rows inserted.")
