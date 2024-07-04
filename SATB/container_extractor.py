from pdfminer.high_level import extract_text
from urllib.request import urlopen
import requests
from bs4 import BeautifulSoup
import io


def given_advisory_to_text(advisory_string: str):
    try:
        return pdf_to_text(advisory_string)
    except:
        try:
            return url_to_text(advisory_string)
        except:
            raise Exception(f"ERROR: Couldn't translate {advisory_string} into text.")



def pdf_to_text(file):
    return extract_text(file)


def url_to_text(url: str) -> str:
    advisory_bytes = io.BytesIO(requests.get(url).content)
    try:
        return pdf_to_text(advisory_bytes)
    except:
        return html_to_text(advisory_bytes)


def html_to_text(advisory_bytes):
    html = advisory_bytes.read()
    soup = BeautifulSoup(html, features="html.parser")

    for script in soup(["script", "style"]):
        script.extract()

    return soup.get_text()