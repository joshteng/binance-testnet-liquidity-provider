import time
from urllib.parse import urlencode


def encoded_string(query):
    return urlencode(query, True).replace("%40", "@")


def get_timestamp():
    return int(time.time() * 1000)


def clean_none_value(d) -> dict:
    out = {}
    for k in d.keys():
        if d[k] is not None:
            out[k] = d[k]
    return out
