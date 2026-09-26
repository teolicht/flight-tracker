import json
import requests
import os
import time
import sys
from rich.live import Live
from rich.table import Table

# PARSE
# Take aircraft.json and populate each aicraft to its own Aircraft object
# Take stats.json and populate into a Stats object or something. Not many fields important here

# QUERY
# Take aicraft hex code and query information from hexdb.io

class Aircraft:
    def __init__(
        self,
        hex: str,
        messages: int,
        seen: float,
        rssi: float,
        squawk: str | None = None,
        flight: str | None = None,
        lat: float | None = None,
        lon: float | None = None,
        altitude: int | None = None,
        vert_rate: int | None = None,
        track: int | None = None,
        speed: int | None = None,
        category: str | None = None,
        registration: str | None = None,
        manufacturer: str | None = None,
        icao_type: str | None = None,
        model: str | None = None,
        owner: str | None = None,
        operator_code: str | None = None,
        route_icao: tuple[str, str] | None = None,
        route_iata: tuple[str, str] | None = None,
        image: str | None = None,
    ):
        self.hex = hex
        self.messages = messages
        self.seen = seen
        self.rssi = rssi
        self.squawk = squawk
        self.flight = flight
        self.lat = lat
        self.lon = lon
        self.altitude = altitude
        self.vert_rate = vert_rate
        self.track = track
        self.speed = speed
        self.category = category
        self.registration = registration
        self.manufacturer = manufacturer
        self.icao_type = icao_type
        self.model = model
        self.owner = owner
        self.operator_code = operator_code
        self.route_icao = route_icao
        self.route_iata = route_iata
        self.image = image

    def update(self, data: dict) -> None:
        # Guaranteed fields
        self.messages = data["messages"]
        self.seen = data["seen"]
        self.rssi = data["rssi"]
        # Fields may be none
        flight = data.get("flight")
        self.flight = flight.strip() if flight is not None else None
        self.squawk = data.get("squawk")
        self.lat = data.get("lat")
        self.lon = data.get("lon")
        self.altitude = data.get("altitude")
        self.vert_rate = data.get("vert_rate")
        self.track = data.get("track")
        self.speed = data.get("speed")
        self.category = data.get("category")

    def coords(self) -> tuple[float, float] | None:
        if self.lat is None or self.lon is None:
            return None
        return self.lat, self.lon


# {hex string: aircraft object}
active_aircraft: dict[str, Aircraft] = {}


def read_json(path: str) -> dict:
    with open(path, "r") as file:
        return json.load(file)


# Run only once when a new aircraft is detected
def enrich_aircraft(ac: Aircraft) -> None:
    """
    Populates aircraft's
        - Registration number
        - Manufacturer
        - ICAO type code
        - Type/model
        - Owner
        - Operator flag code
        - Image
        - Route in ICAO and IATA formats
    """
    # Aircraft info
    r = requests.get(f"https://hexdb.io/api/v1/aircraft/{ac.hex}")
    if r.status_code != 404:
        ac_json = json.loads(r.text)
        ac.registration = ac_json["Registration"]
        ac.manufacturer = ac_json["Manufacturer"]
        ac.icao_type = ac_json["ICAOTypeCode"]
        ac.model = ac_json["Type"]
        ac.owner = ac_json["RegisteredOwners"]
        ac.operator_code = ac_json["OperatorFlagCode"]
    r = requests.get(f"https://hexdb.io/hex-image?hex={ac.hex}")
    if r.status_code != 404:
        ac.image = r.text.strip()
    # Route info
    if ac.flight is not None:
        r = requests.get(f"https://hexdb.io/callsign-route?callsign={ac.flight}")
        if r.status_code != 404:
            dep, des = r.text.strip().split("-")
            ac.route_icao = (dep, des)
        r = requests.get(f"https://hexdb.io/callsign-route-iata?callsign={ac.flight}")
        if r.status_code != 404:
            dep, des = r.text.strip().split("-")
            ac.route_iata = (dep, des)


def aircraft_table(aircraft: dict[str, Aircraft]) -> Table:
    table = Table(title="ADS-B Aircraft")

    table.add_column("Flight")
    table.add_column("Registration")
    table.add_column("Aircraft")
    table.add_column("Owner")
    table.add_column("Position")
    table.add_column("Altitude")
    table.add_column("V/S")
    table.add_column("Speed")
    table.add_column("Track")
    table.add_column("Route")
    table.add_column("RSSI")
    table.add_column("Image")

    for ac in aircraft.values():
        position = (
            f"{ac.lat:.3f}, {ac.lon:.3f}"
            if ac.lat is not None and ac.lon is not None
            else "-"
        )

        route = (
            f"{ac.route_icao[0]}-{ac.route_icao[1]} "
            f"({ac.route_iata[0]}-{ac.route_iata[1]})"
            if ac.route_icao is not None and ac.route_iata is not None
            else "-"
        )

        table.add_row(
            ac.flight or "-",
            ac.registration or "-",
            f"{ac.manufacturer or '-'} {ac.model or '-'}",
            ac.owner or "-",
            position,
            f"{ac.altitude} ft" if ac.altitude is not None else "-",
            f"{ac.vert_rate} fpm" if ac.vert_rate is not None else "-",
            f"{ac.speed} kt" if ac.speed is not None else "-",
            f"{ac.track}°" if ac.track is not None else "-",
            route,
            f"{ac.rssi:.1f} dB",
            ac.image or "-",
        )

    return table

# Main loop
with Live(aircraft_table(active_aircraft), refresh_per_second=1) as live:
    while True:
        for data in read_json(sys.argv[1])["aircraft"]:
            if data["hex"] in active_aircraft:
                active_aircraft[data["hex"]].update(data)
            else:
                obj = Aircraft(
                    data["hex"], data["messages"], data["seen"], data["rssi"]
                )
                obj.update(data)
                enrich_aircraft(obj)
                active_aircraft[data["hex"]] = obj

        live.update(aircraft_table(active_aircraft))

        time.sleep(1)

