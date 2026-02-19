import hashlib
import json
import os
import urllib.parse
import urllib.request
from datetime import date, datetime
from typing import Any, Dict, List, Optional

AMADEUS_AUTH_URL = "https://test.api.amadeus.com/v1/security/oauth2/token"
AMADEUS_OFFERS_URL = "https://test.api.amadeus.com/v2/shopping/flight-offers"
INR_TO_EUR_FALLBACK = 90.0

CITY_TO_IATA = {
    "new delhi": "DEL",
    "delhi": "DEL",
    "mumbai": "BOM",
    "hanoi": "HAN",
    "ho chi minh city": "SGN",
    "da nang": "DAD",
    "phu quoc": "PQC",
}

IATA_TO_CITY = {
    "DEL": ("New Delhi", "India"),
    "BOM": ("Mumbai", "India"),
    "HAN": ("Hanoi", "Vietnam"),
    "SGN": ("Ho Chi Minh City", "Vietnam"),
    "DAD": ("Da Nang", "Vietnam"),
    "PQC": ("Phu Quoc", "Vietnam"),
}


class AmadeusConfigError(ValueError):
    pass


def _http_json(url: str, data: Optional[bytes] = None, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=30) as response:
        payload = response.read().decode("utf-8")
    return json.loads(payload)


def city_to_iata(city: str) -> str:
    code = CITY_TO_IATA.get(city.strip().lower())
    if not code:
        raise AmadeusConfigError(
            f"Unsupported city '{city}'. Add it to CITY_TO_IATA in app/providers/amadeus.py"
        )
    return code


def _get_access_token(client_id: str, client_secret: str) -> str:
    body = urllib.parse.urlencode(
        {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }
    ).encode("utf-8")
    response = _http_json(
        AMADEUS_AUTH_URL,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = response.get("access_token")
    if not token:
        raise RuntimeError(f"Failed to get Amadeus token: {response}")
    return token


def _duration_to_human(iso_duration: str) -> str:
    # PT4H15M -> 4h 15m
    hours = 0
    minutes = 0
    if "T" in iso_duration:
        time_part = iso_duration.split("T", 1)[1]
        if "H" in time_part:
            hours = int(time_part.split("H", 1)[0])
            time_part = time_part.split("H", 1)[1]
        if "M" in time_part:
            minutes = int(time_part.split("M", 1)[0])
    if hours and minutes:
        return f"{hours}h {minutes}m"
    if hours:
        return f"{hours}h"
    return f"{minutes}m"


def _stable_uuid(*parts: str) -> str:
    joined = "|".join(parts)
    digest = hashlib.sha256(joined.encode("utf-8")).hexdigest()
    return digest[:32]


def _to_inr(price_total: str, currency: str) -> int:
    value = float(price_total)
    if currency == "INR":
        return round(value)
    if currency == "EUR":
        return round(value * INR_TO_EUR_FALLBACK)
    return round(value * INR_TO_EUR_FALLBACK)


def fetch_flights(
    origin: str,
    destination: str,
    start_date: date,
    end_date: date,
    adults: int = 1,
    max_per_day: int = 10,
) -> List[Dict[str, Any]]:
    client_id = os.getenv("AMADEUS_CLIENT_ID")
    client_secret = os.getenv("AMADEUS_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise AmadeusConfigError("AMADEUS_CLIENT_ID and AMADEUS_CLIENT_SECRET must be set")

    origin_iata = city_to_iata(origin)
    destination_iata = city_to_iata(destination)

    token = _get_access_token(client_id, client_secret)

    rows: List[Dict[str, Any]] = []
    current = start_date
    while current <= end_date:
        params = urllib.parse.urlencode(
            {
                "originLocationCode": origin_iata,
                "destinationLocationCode": destination_iata,
                "departureDate": current.isoformat(),
                "adults": adults,
                "max": max_per_day,
                "currencyCode": "INR",
                "nonStop": "false",
            }
        )
        response = _http_json(
            f"{AMADEUS_OFFERS_URL}?{params}",
            headers={"Authorization": f"Bearer {token}"},
        )

        offers = response.get("data", [])
        for offer in offers:
            itinerary = offer["itineraries"][0]
            segments = itinerary["segments"]
            carrier = segments[0].get("carrierCode", "Unknown")
            duration = _duration_to_human(itinerary.get("duration", ""))
            is_nonstop = len(segments) == 1
            dep = datetime.fromisoformat(segments[0]["departure"]["at"])

            city_origin, country_origin = IATA_TO_CITY.get(origin_iata, (origin, "Unknown"))
            city_destination, country_destination = IATA_TO_CITY.get(destination_iata, (destination, "Unknown"))

            rows.append(
                {
                    "uuid": _stable_uuid(origin_iata, destination_iata, dep.isoformat(), str(offer["price"]["total"]), carrier),
                    "airline": carrier,
                    "date": dep.date().isoformat(),
                    "duration": duration,
                    "flightType": "Nonstop" if is_nonstop else "Connecting",
                    "price_inr": _to_inr(offer["price"]["total"], offer["price"].get("currency", "INR")),
                    "origin": city_origin,
                    "destination": city_destination,
                    "originCountry": country_origin,
                    "destinationCountry": country_destination,
                    "link": "",
                    "rainProbability": None,
                    "freeMeal": None,
                }
            )
        current = current.fromordinal(current.toordinal() + 1)

    return rows
