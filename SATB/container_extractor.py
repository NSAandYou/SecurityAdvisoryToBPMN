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
    try:
        return pdf_to_text(io.BytesIO(requests.get(url).content))
    except:
        return html_to_text(urlopen(url).read())


def html_to_text(html):
    soup = BeautifulSoup(html, features="html.parser")
    for script in soup(["script", "style"]):
        script.extract()
    text = soup.get_text()

    return text


if __name__ == "__main__":
    print("!"+url_to_text("https://learn.microsoft.com/en-us/security-updates/securitybulletins/2017/ms17-014"))
    ##print("!"+url_to_text("https://sps.honeywell.com/content/dam/honeywell-edam/sps/ppr/en-us/public/support/cyber-security-notifications/sps-ppr-vc-xss-security-notification.pdf"))

