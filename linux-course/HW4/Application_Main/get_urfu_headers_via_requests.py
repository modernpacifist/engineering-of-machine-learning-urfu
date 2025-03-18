#!/bin/env python3.8
import requests as rq

from bs4 import BeautifulSoup


res = rq.get("https://urfu.ru")
print(f"request headers: {res.headers}")

response_text = res.text

soup = BeautifulSoup(response_text, 'html.parser')
headers = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])

if len(headers) != 0:
    print("html headers:")
    for header in headers:
        print(header.text)
