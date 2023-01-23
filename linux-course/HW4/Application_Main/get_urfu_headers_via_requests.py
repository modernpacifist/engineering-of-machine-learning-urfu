#!/bin/env python3.8

import requests as rq

res = rq.get("https://urfu.ru")

print(str(res.headers))
