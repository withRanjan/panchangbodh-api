from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import datetime
import swisseph as swe
import os

# Set ephemeris path to 'ephe' subdirectory with absolute path
swe.set_ephe_path(os.path.abspath("ephe"))

app = FastAPI(
    title="PanchangBodh API",
    description="Dynamic Daily Panchang API for any date/city. Powered by Swiss Ephemeris.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CITY_COORDS = {
    "delhi": (28.6139, 77.2090),
    "mumbai": (19.0760, 72.8777),
    "kolkata": (22.5726, 88.3639),
    "chennai": (13.0827, 80.2707),
    "bengaluru": (12.9716, 77.5946),
    "hyderabad": (17.3850, 78.4867),
    "pune": (18.5204, 73.8567)
}
DEFAULT_CITY = "delhi"

def format_time_from_float(t):
    hour = int(t)
    minute = int(round((t - hour) * 60))
    ampm = "AM" if hour < 12 or hour == 24 else "PM"
    hour12 = hour % 12
    hour12 = 12 if hour12 == 0 else hour12
    return f"{hour12:02}:{minute:02} {ampm}"

def calculate_sun_times(lat, lon, year, month, day, timezone=5.5):
    jd = swe.julday(year, month, day)
    try:
        sunrise_ut = swe.rise_trans(jd, swe.SUN, lon, lat, rsmi=swe.CALC_RISE | swe.BIT_DISC_CENTER)[1][0]
        sunset_ut  = swe.rise_trans(jd, swe.SUN, lon, lat, rsmi=swe.CALC_SET | swe.BIT_DISC_CENTER)[1][0]
    except Exception:
        return ("N/A", "N/A")
    sunrise = sunrise_ut + timezone
    sunset  = sunset_ut + timezone
    if sunrise < 0: sunrise += 24
    if sunset < 0: sunset += 24
    if sunrise >= 24: sunrise -= 24
    if sunset >= 24: sunset -= 24
    return format_time_from_float(sunrise), format_time_from_float(sunset)

def get_tithi(jd):
    sun_long = swe.calc_ut(jd, swe.SUN)[0][0]
    moon_long = swe.calc_ut(jd, swe.MOON)[0][0]
    tithi_num = int(((moon_long - sun_long) % 360) / 12) + 1
    paksha = "Shukla" if tithi_num <= 15 else "Krishna"
    tithi_names = [
        "Pratipada", "Dvitiya", "Tritiya", "Chaturthi", "Panchami", "Shashthi",
        "Saptami", "Ashtami", "Navami", "Dashami", "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Purnima/Amavasya"
    ]
    tithi_idx = (tithi_num-1) % 15
    tithi_name = tithi_names[tithi_idx]
    return tithi_name, paksha

def get_nakshatra(jd):
    moon_long = swe.calc_ut(jd, swe.MOON)[0][0]
    nak_num = int(moon_long / (360/27)) + 1
    nak_names = [
        "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashirsha", "Ardra", "Punarvasu",
        "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta",
        "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha",
        "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada",
        "Uttara Bhadrapada", "Revati"
    ]
    nakshatra_name = nak_names[(nak_num-1) % 27]
    return nakshatra_name

def get_rahu_kaal(weekday, sunrise, sunset):
    rahu_sequence = [7, 1, 6, 4, 5, 3, 2]  # Mon to Sun (0=Mon)
    start_index = rahu_sequence[weekday]
    def time_to_float(t):
        h, m, ampm = int(t[:2]), int(t[3:5]), t[-2:]
        if ampm == "PM" and h != 12: h += 12
        if ampm == "AM" and h == 12: h = 0
        return h + m/60
    s_rise = time_to_float(sunrise)
    s_set = time_to_float(sunset)
    if s_set < s_rise: s_set += 24
    day_length = s_set - s_rise
    rahu_start = s_rise + (day_length / 8) * (start_index-1)
    rahu_end = rahu_start + (day_length / 8)
    return format_time_from_float(rahu_start), format_time_from_float(rahu_end)

@app.get("/api/panchang")
async def panchang(
    city: str = Query(DEFAULT_CITY),
    date: str = Query("2025-07-15"),
    lang: str = Query("en")
):
    try:
        city_clean = city.strip().lower()
        lat, lon = CITY_COORDS.get(city_clean, CITY_COORDS[DEFAULT_CITY])
        city_name = city_clean.title() if city_clean in CITY_COORDS else DEFAULT_CITY.title()
        dt = datetime.datetime.strptime(date, "%Y-%m-%d")
        jd = swe.julday(dt.year, dt.month, dt.day)
        sunrise, sunset = calculate_sun_times(lat, lon, dt.year, dt.month, dt.day)
        if sunrise == "N/A" or sunset == "N/A":
            rahu_start, rahu_end = "N/A", "N/A"
        else:
            rahu_start, rahu_end = get_rahu_kaal(dt.weekday(), sunrise, sunset)
        tithi, paksha = get_tithi(jd)
        nakshatra = get_nakshatra(jd)
        weekday = dt.strftime("%A")
        panchang = {
            "city": city_name,
            "date": date,
            "weekday": weekday,
            "sunrise": sunrise,
            "sunset": sunset,
            "tithi": tithi,
            "paksha": paksha,
            "nakshatra": nakshatra,
            "rahu_kaal": f"{rahu_start} – {rahu_end}"
        }
        return panchang
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/debug/files")
def list_ephe_files():
    # List .se1 files in ephe directory and show absolute path for debug
    ephe_path = os.path.abspath("ephe")
    try:
        files = [f for f in os.listdir(ephe_path) if f.endswith(".se1")]
    except Exception as ex:
        return {"error": str(ex), "cwd": os.getcwd(), "ephe_path": ephe_path}
    return {"se1_files": files, "cwd": os.getcwd(), "ephe_path": ephe_path}

@app.on_event("startup")
def print_ephe_debug():
    ephe_path = os.path.abspath("ephe")
    print(f"Startup: Swiss Ephemeris path set to: {ephe_path}")
    print(f"Startup: CWD is: {os.getcwd()}")
    try:
        print(f"Startup: .se1 files: {os.listdir(ephe_path)}")
    except Exception as ex:
        print(f"Startup: Could not list .se1 files: {ex}")

@app.get("/")
def root():
    return {
        "msg": "PanchangBodh API is running!",
        "usage": "Call /api/panchang?city=delhi&date=2025-07-15"
    }
