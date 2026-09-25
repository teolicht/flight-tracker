import json
import requests

# PARSE
# Take aircraft.json and populate each aicraft to its own Aircraft object
# Take stats.json and populate into a Stats object or something. Not many fields important here

# QUERY
# Take aicraft hex code and query information from hexdb.io

# IMPORTANT: keep a cache of currently tracked aircraft .Do NOT run specially enrich_aircraft() every time
# aircraft.json is updated, since it makes a bunch of HTTP requests and takes a while.
aircraft_cache = []

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

    def coords(self) -> tuple[float, float] | None:
        if self.lat is None or self.lon is None:
            return None
        return self.lat, self.lon



def parse_aircraft() -> list[Aircraft]:
    # TODO: proper relative path
    with open("json/aircraft.json", "r") as file:
        json_str = file.read()
    acs = json.loads(json_str)

    ac_objs = []
    for ac in acs["aircraft"]:
        obj = Aircraft(ac["hex"], ac["messages"], ac["seen"], ac["rssi"])
        if "squawk" in ac:
            obj.squawk = ac["squawk"]
        if "flight" in ac:
            # For some reason the flight numbers have spaces in the end
            obj.flight = ac["flight"].strip() 
        if "lat" in ac:
            obj.lat = ac["lat"]
        if "lon" in ac:
            obj.lon = ac["lon"]
        if "altitude" in ac:
            obj.altitude = ac["altitude"]
        if "vert_rate" in ac:
            obj.vert_rate = ac["vert_rate"]
        if "track" in ac:
            obj.track = ac["track"]
        if "speed" in ac:
            obj.speed = ac["speed"]
        if "category" in ac:
            obj.category = ac["category"]
        ac_objs.append(obj)

    return ac_objs


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



acs = parse_aircraft()
for ac in acs:
    enrich_aircraft(ac)

