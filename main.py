from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import datetime
import swisseph as swe

# ----------- FastAPI App Setup -----------
app = FastAPI()

# Enable CORS for all domains (you can restrict this in prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------- Basic City Lookup Table -----------
# For more cities, just add their (latitude, longitude)
CITY_COORDS = {
    "delhi": (28.6139, 77.2090),
    "mumbai": (19.0760, 72.8777),
    "kolkata": (22.5726, 88.3639),
    "chennai": (13.0827, 80.2707),
    "bengaluru": (12.9716, 77.5946),
    "hyderabad": (17.3850, 78.4867),
    "pune": (18.5204, 73.8567)
    # Add more as needed!
}

# ----------- Utility Functions -----------

def format_time_from_float(t):
    """
    Convert decimal hour (e.g. 5.5) to HH:MM AM/PM format.
    Handles times past 12 PM correctly.
    """
    hour = int(t)
    minute = int((t - hour) * 60)
    ampm = "AM" if hour < 12 or hour == 24 else "PM"
    hour12 = hour % 12
    hour12 = 12 if hour12 == 0 else hour12
    return f"{hour12:02}:{minute:02} {ampm}"

def calculate_sun_times(lat, lon, year, month, day, timezone=5.5):
    """
    Calculate local sunrise and sunset using Swiss Ephemeris.
    Returns (sunrise, sunset) as strings.
    """
    jd = swe.julday(year, month, day)
    # Swiss Ephemeris expects longitude as East positive, latitude North positive
    # Calculate sunrise
    try:
        sunrise_ut = swe.rise_trans(jd, swe.SUN, lon, lat, rsmi=swe.CALC_RISE | swe.BIT_DISC_CENTER)[1][0]
        sunset_ut  = swe.rise_trans(jd, swe.SUN, lon, lat, rsmi=swe.CALC_SET | swe.BIT_DISC_CENTER)[1][0]
    except Exception:
        # In rare cases (arctic circle, etc), return None
        return ("N/A", "N/A")
    sunrise = sunrise_ut + timezone
    sunset  = sunset_ut + timezone
    # Adjust for 24-hour wrap-around
    if sunrise < 0: sunrise += 24
    if sunset < 0: sunset += 24
    if sunrise >= 24: sunrise -= 24
    if sunset >= 24: sunset -= 24
    return format_time_from_float(sunrise), format_time_from_float(sunset)

def get_tithi(jd):
    """
    Calculate tithi name and paksha for given Julian day.
    """
    # Calculate Sun and Moon longitudes
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
    """
    Calculate nakshatra name for given Julian day.
    """
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
    """
    Calculate Rahu Kaal time window for given weekday and sunrise/sunset.
    Returns (start, end) as strings.
    """
    # Rahu Kaal's order for Mon-Sun (0=Monday)
    rahu_sequence = [7, 1, 6, 4, 5, 3, 2]  # Mon to Sun
    start_index = rahu_sequence[weekday]
    # Convert times to float hours for calculation
    def time_to_float(t):
        h, m, ampm = int(t[:2]), int(t[3:5]), t[-2:]
        if ampm == "PM" and h != 12:
            h += 12
        if ampm == "AM" and h == 12:
            h = 0
        return h + m/60
    s_rise = time_to_float(sunrise)
    s_set = time_to_float(sunset)
    # In case sunset is past midnight (rare)
    if s_set < s_rise:
        s_set += 24
    day_length = s_set - s_rise
    rahu_start = s_rise + (day_length / 8) * (start_index-1)
    rahu_end = rahu_start + (day_length / 8)
    return format_time_from_float(rahu_start), format_time_from_float(rahu_end)

# ----------- Panchang API Route -----------

@app.get("/api/panchang")
async def panchang(
    city: str = Query("delhi"), 
    date: str = Query("2025-07-15"), 
    lang: str = Query("en")
):
    """
    Panchang API endpoint.
    Accepts city and date, returns dynamic Panchang for that day/city.
    """
    try:
        # --- Resolve city coordinates ---
        city = city.lower()
        lat, lon = CITY_COORDS.get(city, (28.6139, 77.2090))  # default: Delhi

        # --- Parse date and get Julian day ---
        dt = datetime.datetime.strptime(date, "%Y-%m-%d")
        jd = swe.julday(dt.year, dt.month, dt.day)

        # --- Calculate sunrise & sunset ---
        sunrise, sunset = calculate_sun_times(lat, lon, dt.year, dt.month, dt.day)
        
        # --- Calculate tithi, paksha, nakshatra ---
        tithi, paksha = get_tithi(jd)
        nakshatra = get_nakshatra(jd)
        weekday = dt.strftime("%A")

        # --- Calculate Rahu Kaal ---
        weekday_num = dt.weekday()  # 0=Monday
        rahu_start, rahu_end = get_rahu_kaal(weekday_num, sunrise, sunset)

        # --- Compose Panchang Dictionary ---
        panchang = {
            "city": city.title(),
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
        # Return error if something fails
        return {"success": False, "error": str(e)}

@app.get("/")
def root():
    """
    Root endpoint for health check / usage info.
    """
    return {
        "msg": "Dynamic Panchang API running! Try /api/panchang?city=delhi&date=2025-07-15"
    }

