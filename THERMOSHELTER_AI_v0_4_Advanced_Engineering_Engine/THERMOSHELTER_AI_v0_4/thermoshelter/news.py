import requests
import streamlit as st
from datetime import datetime

@st.cache_data(ttl=1800, show_spinner=False)
def _fetch_news(city, state):
    query = f'("{city}" OR "{state}") AND (weather OR heatwave OR rainfall OR flood OR cyclone OR climate OR temperature)'
    params = {"query": query, "mode":"ArtList", "format":"json", "sort":"DateDesc", "maxrecords":10,
              "timespan":"7d", "sourcelang":"eng"}
    response = requests.get("https://api.gdeltproject.org/api/v2/doc/doc", params=params, timeout=18)
    response.raise_for_status()
    payload = response.json()
    items = []
    for article in payload.get("articles", []):
        title = article.get("title")
        url = article.get("url")
        if not title or not url:
            continue
        raw_date = article.get("seendate", "")
        try:
            date = datetime.strptime(raw_date[:14], "%Y%m%d%H%M%S").strftime("%d %b %Y, %H:%M UTC")
        except Exception:
            date = raw_date or "Recent"
        items.append({"title":title, "url":url, "source":article.get("domain","News source"), "date":date})
    return items

def get_local_news(city, state, refresh=False):
    try:
        if refresh:
            _fetch_news.clear()
        return _fetch_news(city, state)
    except (requests.RequestException, ValueError):
        return []
