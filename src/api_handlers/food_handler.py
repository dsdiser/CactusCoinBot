import random
from openfoodfacts import API, Country
from openfoodfacts.types import COUNTRY_CODE_TO_NAME
USER_AGENT = "CactusCoinBot/1.0"


def format_country(country: str) -> str:
    # formats string like "en:united-states" to "United States"
    country_formatted = country[3:]
    country_words = [word.capitalize() for word in country_formatted.split('-')]
    return " ".join(country_words)


def generate_food_questions():
    # Come up with a randomized list of 20 counties
    country_codes = random.choices(COUNTRY_CODE_TO_NAME.keys(), k=20)
    # Get food items for each of them
    for country_code in country_codes:
        # pull 20 products
        api = API(user_agent="CactusCoinBot/1.0", country=country_code)
        results = api.product.text_search("", sort_by="last_modified_t")
        products = results["products"]
        for product in products:
            countries = product.get("countries_tags", None)
            product_name = product.get("product_name_en", None)
            image_url = product.get("image_url", None)
            barcode_id = product.get("id", None)
            if not countries or not product_name or not image_url or not barcode_id:
                continue

        # create list of objects to insert into DB, then just insert with field for used

    # Parse them into usable display objects using the countries for other food items

def get_food_items():
    api = API(user_agent="CactusCoinBot/1.0", country=Country.fr)
    results = api.product.text_search("")
    products = results["products"]
    for product in products:
        countries = product.get("countries_tags", None)
        product_name = product.get("product_name_en", None)
        image_url = product.get("image_url", None)
        if not countries or not product_name or not image_url:
            continue
        # format countries into normal capitalization
        countries = [format_country(country) for country in countries]
        print(product_name, countries, image_url)

get_food_items()