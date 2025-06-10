from fastapi import FastAPI, Query
from bs4 import BeautifulSoup
import httpx

app = FastAPI()


# URL of Vietlex, which word on A1 A2 B1
BASE_URL = "https://vietlex.com/tu-dien/english-vietnamese/"

import requests
from bs4 import BeautifulSoup


@app.get("/translate")
async def translate(word: str = Query(..., min_length=1)):
    url = BASE_URL
    
    async with httpx.AsyncClient() as client:
        payload = {
        "targetDiv": word,
        "nhap": "Tra từ"
    }

    headers = {
        "User-Agent": "Mozilla/5.0",
        'Accept': 'application/json;charset=utf-8',
        'Accept-Charset': 'UTF-8'
    }

    response = requests.post(url, data=payload, headers=headers)
    response.encoding = 'utf-8'
    if response.status_code != 200:
        return {"error": "Failed to fetch the meaning"}

    soup = BeautifulSoup(response.text, "html.parser")

    # Lấy bảng kết quả
    table = soup.select_one("center > table")
    if not table:
        return {"error": "No result found"}

    rows = table.find_all("tr")

    meanings = []
    current_word = ""
    for row in rows:
        cols = row.find_all("td")
        if len(cols) == 2 and "font" in str(cols[1]):
            # nghĩa của từ
            meaning_text = cols[1].get_text(separator="\n", strip=True)
            meaning_text = meaning_text.replace("▶", "").replace("○", "").strip()
            meanings.append(meaning_text)
        elif len(cols) == 2:
            current_word = cols[1].get_text(strip=True)

    return {
        "word": word,
        "meanings": meanings
    }
