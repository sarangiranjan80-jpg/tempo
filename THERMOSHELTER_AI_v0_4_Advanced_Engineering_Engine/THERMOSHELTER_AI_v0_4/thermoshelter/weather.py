import requests
import streamlit as st

BASE = "https://api.open-meteo.com/v1/forecast"

@st.cache_data(ttl=900, show_spinner=False)
def _fetch_weather(lat, lon):
    params = {
        "latitude": lat, "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,weather_code,wind_speed_10m",
        "hourly": "temperature_2m,relative_humidity_2m,precipitation_probability,precipitation,wind_speed_10m,shortwave_radiation",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,uv_index_max",
        "forecast_days": 7, "timezone": "auto"
    }
    response = requests.get(BASE, params=params, timeout=15)
    response.raise_for_status()
    return response.json()

def get_weather(lat, lon, refresh=False):
    try:
        if refresh:
            _fetch_weather.clear()
        return _fetch_weather(float(lat), float(lon))
    except requests.RequestException as exc:
        return {"error": str(exc)}

def weather_summary(data):
    current = data.get("current", {})
    code = current.get("weather_code")
    descriptions = {0:"Clear sky",1:"Mainly clear",2:"Partly cloudy",3:"Overcast",45:"Fog",48:"Depositing rime fog",
        51:"Light drizzle",53:"Drizzle",55:"Dense drizzle",61:"Light rain",63:"Rain",65:"Heavy rain",
        71:"Light snow",73:"Snow",75:"Heavy snow",80:"Rain showers",81:"Rain showers",82:"Violent rain showers",
        95:"Thunderstorm",96:"Thunderstorm with hail",99:"Severe thunderstorm"}
    def val(key):
        return current.get(key)
    return {
        "temperature": val("temperature_2m"),
        "humidity": val("relative_humidity_2m"),
        "wind": val("wind_speed_10m"),
        "uv": (data.get("daily",{}).get("uv_index_max") or [None])[0],
        "condition": descriptions.get(code, "Conditions unavailable")
    }
