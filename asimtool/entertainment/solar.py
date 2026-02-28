"""Solar energy optimizer — weather data + efficiency calculations."""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests


# Country code → full name for Nominatim
_COUNTRY_NAMES = {
    "NL": "Netherlands", "TR": "Turkey", "US": "United States",
    "GB": "United Kingdom", "DE": "Germany", "FR": "France",
    "IT": "Italy", "ES": "Spain",
}


def _geocode(postal_code: str, country: str = "") -> tuple:
    """Resolve *postal_code* → (lat, lon, location_name) using free APIs."""
    lat = lon = None
    location_name = "Unknown"

    # Method 1: Open-Meteo Geocoding
    try:
        query = f"{postal_code}, {country}" if country else postal_code
        resp = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": query, "count": 1, "language": "en", "format": "json"},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            if "results" in data and data["results"]:
                r = data["results"][0]
                lat, lon = r["latitude"], r["longitude"]
                location_name = r.get("name", "Unknown")
                if "admin1" in r:
                    location_name += f", {r['admin1']}"
                if "country" in r:
                    location_name += f", {r['country']}"
    except Exception:
        pass

    # Method 2: Nominatim (best for European postal codes)
    if lat is None:
        try:
            country_full = _COUNTRY_NAMES.get(country.upper(), country) if country else ""
            q = f"{postal_code}, {country_full}" if country_full else postal_code
            resp = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": q, "format": "json", "limit": 1, "addressdetails": 1},
                headers={"User-Agent": "asimtool/1.0 (solar optimizer)"},
                timeout=10,
            )
            if resp.status_code == 200:
                results = resp.json()
                if results:
                    r = results[0]
                    lat, lon = float(r["lat"]), float(r["lon"])
                    addr = r.get("address", {})
                    parts = []
                    for key in ("city", "town", "village", "municipality"):
                        if key in addr:
                            parts.append(addr[key])
                            break
                    if "country" in addr:
                        parts.append(addr["country"])
                    location_name = ", ".join(parts) if parts else r.get("display_name", "Unknown")
        except Exception:
            pass

    return lat, lon, location_name


def optimize_solar(
    postal_code: str,
    country: str = "",
    target_date: str | None = None,
) -> Dict[str, Any]:
    """Calculate optimal solar energy hours for a location.

    Uses **free** Open-Meteo and Nominatim APIs — no API keys required.

    Parameters
    ----------
    postal_code : str
        Postal code or city name.
    country : str
        Country code or name (e.g. ``"NL"``, ``"Germany"``).
    target_date : str, optional
        ``"YYYY-MM-DD"`` date to optimise for (default today).

    Returns
    -------
    dict
        Keys: ``location``, ``lat``, ``lon``, ``target_date``,
        ``target_date_display``, ``weather``, ``sun_times``,
        ``optimal_hours``, ``week_forecast``, ``recommendations``.

    Example
    -------
    >>> from asimtool.entertainment import optimize_solar
    >>> result = optimize_solar("1011", country="NL")
    >>> print(result["location"], result["weather"]["description"])
    """
    if not postal_code.strip():
        raise ValueError("Postal code is required.")

    lat, lon, location_name = _geocode(postal_code.strip(), country.strip())
    if lat is None or lon is None:
        raise ValueError(f"Unable to find location for '{postal_code}'.")

    today_dt = datetime.today()
    try:
        target_dt = datetime.strptime(target_date, "%Y-%m-%d") if target_date else today_dt
    except ValueError:
        target_dt = today_dt

    today_str = today_dt.strftime("%Y-%m-%d")
    target_date_str = target_dt.strftime("%Y-%m-%d")
    end_date_str = (today_dt + timedelta(days=6)).strftime("%Y-%m-%d")
    target_date_display = target_dt.strftime("%A, %B %d, %Y")

    # Fetch weather from Open-Meteo (free)
    weather_resp = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat, "longitude": lon,
            "daily": "sunrise,sunset",
            "hourly": "cloudcover,temperature_2m",
            "timezone": "auto",
            "start_date": today_str, "end_date": end_date_str,
        },
        timeout=10,
    )
    if weather_resp.status_code != 200:
        raise RuntimeError(f"Weather API failed ({weather_resp.status_code}).")

    wd = weather_resp.json()
    hourly = wd.get("hourly", {})
    daily = wd.get("daily", {})

    hourly_times = hourly.get("time", [])
    hourly_clouds = hourly.get("cloudcover", [])
    hourly_temps = hourly.get("temperature_2m", [])
    daily_times = daily.get("time", [])

    target_day_idx = daily_times.index(target_date_str) if target_date_str in daily_times else 0
    h_start = target_day_idx * 24
    target_clouds = hourly_clouds[h_start:h_start + 24]
    target_temps = hourly_temps[h_start:h_start + 24]

    clouds = target_clouds[12] if len(target_clouds) > 12 else (target_clouds[0] if target_clouds else 50)
    temp = target_temps[12] if len(target_temps) > 12 else (target_temps[0] if target_temps else 20)
    avg_clouds = sum(target_clouds) / len(target_clouds) if target_clouds else 50

    if avg_clouds < 20:
        description = "Clear sky"
    elif avg_clouds < 50:
        description = "Partly cloudy"
    elif avg_clouds < 80:
        description = "Cloudy"
    else:
        description = "Overcast"

    current_weather = {
        "temp": round(temp, 1),
        "description": description,
        "clouds": int(round(avg_clouds)),
        "humidity": 60,
    }

    # 7-day forecast
    week_forecast: List[Dict] = []
    for day_i, day_date in enumerate(daily_times):
        d_start = day_i * 24
        dc = hourly_clouds[d_start:d_start + 24]
        avg_dc = sum(dc) / len(dc) if dc else 50
        avg_eff = max(0, round((100 - avg_dc) * 0.85))
        try:
            day_dt = datetime.strptime(day_date, "%Y-%m-%d")
            day_short = "Today" if day_date == today_str else day_dt.strftime("%a")
        except Exception:
            day_short = day_date[-5:]
        week_forecast.append({
            "date": day_date, "day_short": day_short,
            "avg_efficiency": avg_eff, "clouds": int(round(avg_dc)),
        })

    # Sunrise / sunset
    sunrise_str = daily.get("sunrise", [""])[target_day_idx] if daily.get("sunrise") else ""
    sunset_str = daily.get("sunset", [""])[target_day_idx] if daily.get("sunset") else ""

    sunrise_time = (
        datetime.fromisoformat(sunrise_str.replace("Z", "+00:00"))
        if sunrise_str else datetime.now().replace(hour=6, minute=0)
    )
    sunset_time = (
        datetime.fromisoformat(sunset_str.replace("Z", "+00:00"))
        if sunset_str else datetime.now().replace(hour=18, minute=0)
    )
    solar_noon = sunrise_time + (sunset_time - sunrise_time) / 2
    daylight_duration = (sunset_time - sunrise_time).total_seconds() / 3600

    sun_times = {
        "sunrise": sunrise_time.strftime("%H:%M"),
        "solar_noon": solar_noon.strftime("%H:%M"),
        "sunset": sunset_time.strftime("%H:%M"),
        "daylight_hours": round(daylight_duration, 1),
    }

    # Optimal hours
    optimal_hours: List[Dict] = []
    cloud_factor = (100 - current_weather["clouds"]) / 100
    min_efficiency = 15
    current_hour = sunrise_time.replace(minute=0, second=0, microsecond=0)

    while current_hour < sunset_time:
        hours_from_noon = abs((current_hour - solar_noon).total_seconds() / 3600)
        max_angle = 90 - abs(lat)
        sun_angle = (
            max(0, max_angle * (1 - hours_from_noon / (daylight_duration / 2)))
            if daylight_duration > 0 else 0
        )
        angle_eff = (sun_angle / max_angle) * 100 if max_angle > 0 else 0
        weather_eff = max(min_efficiency, angle_eff * cloud_factor)
        eff = round(weather_eff)
        if eff > 5 and sunrise_time <= current_hour <= sunset_time:
            optimal_hours.append({
                "time": current_hour.strftime("%H:%M"),
                "efficiency": eff,
                "sun_angle": round(sun_angle, 1),
            })
        current_hour += timedelta(hours=1)

    optimal_hours.sort(key=lambda x: x["efficiency"], reverse=True)

    # Recommendations
    recommendations: List[str] = []
    if current_weather["clouds"] < 30:
        recommendations.append("Excellent conditions! Clear skies for maximum solar energy production.")
    elif current_weather["clouds"] < 60:
        recommendations.append("Good conditions with partial clouds. Expect 60-80% efficiency.")
    else:
        recommendations.append("Cloudy conditions reduce efficiency, but panels still produce 15-40% capacity.")

    if optimal_hours:
        best = optimal_hours[:3]
        times = ", ".join(h["time"] for h in best)
        avg_e = sum(h["efficiency"] for h in best) // len(best)
        recommendations.append(f"Best production hours: {times} (avg. {avg_e}% efficiency)")

    if daylight_duration < 10:
        recommendations.append("Short daylight hours — consider battery storage for nighttime use.")
    else:
        recommendations.append(f"{round(daylight_duration, 1)} hours of daylight on {target_date_display}.")

    recommendations.append("Clean solar panels regularly to maintain 95%+ efficiency.")

    return {
        "location": location_name,
        "lat": lat,
        "lon": lon,
        "target_date": target_date_str,
        "target_date_display": target_date_display,
        "week_forecast": week_forecast,
        "weather": current_weather,
        "sun_times": sun_times,
        "optimal_hours": optimal_hours,
        "recommendations": recommendations,
    }
