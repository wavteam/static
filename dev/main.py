import json
import jsoneditor
import logging
import re
import requests
from dataclasses import dataclass
from fake_useragent import UserAgent
from pprint import pprint

ua = UserAgent()

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)

with open("service.json", "r", encoding="UTF-8") as file:
    base = json.loads(file.read())

phone_pattern_legacy = re.compile(r'\{formatted_phone:(.*)}')
phone_pattern = re.compile(r'\{phone:([^}]*)}')


def format_phone(phone, mask):
    formatted_phone = []
    phone_index = 0
    for symbol in mask:
        if phone_index < len(phone):
            if symbol == '*':
                formatted_phone.append(phone[phone_index])
                phone_index += 1
            else:
                formatted_phone.append(symbol)
    return ''.join(formatted_phone)


def format_by_pattern(input_string, phone):
    new_string = input_string

    match_legacy = phone_pattern_legacy.search(input_string)
    if match_legacy:
        new_string = new_string.replace(
            match_legacy.group(),
            format_phone(str(phone), match_legacy.group(1))
        )

    match = phone_pattern.search(input_string)
    if match:
        new_string = new_string.replace(
            match.group(),
            format_phone(phone.phone, match.group(1))
        )

    return new_string.replace("{full_phone}", str(phone)).replace("{phone}", phone.phone)


def process_request(request):
    url = format_by_pattern(request["url"], phone)
    logging.info("URL: %s", url)

    params = {
        "method": request["method"],
        "url": url,
        "headers": {"User-Agent": ua.random}
    }

    logging.info("Method: %s", request["method"].upper())

    if "headers" in request:
        for k, v in request["headers"].items():
            formatted_key = format_by_pattern(k, phone)
            formatted_value = format_by_pattern(v, phone)
            params["headers"][formatted_key] = formatted_value

        logging.info("Headers: %s", params["headers"])

    if "json" in request:
        json_body = format_by_pattern(json.dumps(request["json"]), phone)

        try:
            json.loads(json_body)
        except Exception as e:
            logging.warning("INVALID JSON BODY: %s, Error: %s", json_body, str(e))

        logging.debug("JSON Body: %s", json_body)

        params["json"] = json_body

    if "data" in request:
        formdata = {
            format_by_pattern(k, phone): format_by_pattern(v, phone)
            for k, v in request["data"].items()
        }

        logging.debug("Form data Body: %s", formdata)

        params["data"] = formdata

    logging.debug("Sending request with params: %s", params)

    try:
        response = requests.request(**params)
        try:
            pprint(response.json())
        except json.JSONDecodeError:
            print(response.text)
    except requests.RequestException as e:
        logging.error("Request failed: %s", str(e))


def on_result(result):
    print(json.dumps(result))

    with open("service.json", "w", encoding="UTF-8") as file:
        file.write(json.dumps(result))

    if "requests" in result:
        for index, request in enumerate(result["requests"]):
            logging.info("Request #%s", index)
            process_request(request)
    else:
        process_request(result)


@dataclass
class Phone:
    country_code: str
    phone: str

    def __str__(self):
        return self.country_code + self.phone


country_code = input("Enter country code (7): ")

if not country_code.strip():
    country_code = "7"

phone = Phone(
    country_code,
    input("Enter phone number: ")
)

logging.info(phone)

jsoneditor.editjson(base, callback=on_result)
