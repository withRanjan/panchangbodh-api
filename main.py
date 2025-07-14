from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import datetime

app = FastAPI()

# Allow all origins for widget demo (tighten for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MOCK PANCHANG DATA GENERATOR ---
def get_panchang(city, date, lang):
    # Simulate real panchang - replace with Swiss Ephemeris logic later!
    city = city.title()
    dt = datetime.datetime.strptime(date, "%Y-%m-%d")
    weekday = dt.strftime("%A")
    festivals = ["Guru Purnima"] if dt.strftime("%m-%d") == "07-15" else []
    en = {
        "city": city,
        "date": date,
        "weekday": weekday,
        "tithi": "Purnima",
        "paksha": "Shukla",
        "nakshatra": "Uttara Ashadha",
        "yoga": "Brahma",
        "karana": "Vishti",
        "sunrise": "05:07 AM",
        "sunset": "06:47 PM",
        "moonrise": "07:30 PM",
        "rahu_kaal": "04:30 PM – 06:00 PM",
        "samvat": "2082",
        "festivals": festivals,
    }
    hi = {
        "city": city,
        "date": date,
        "weekday": "सोमवार",
        "tithi": "पूर्णिमा",
        "paksha": "शुक्ल",
        "nakshatra": "उत्तराषाढ़ा",
        "yoga": "ब्रह्म",
        "karana": "विष्टि",
        "sunrise": "05:07 पूर्वाह्न",
        "sunset": "06:47 अपराह्न",
        "moonrise": "07:30 अपराह्न",
        "rahu_kaal": "04:30 अपराह्न – 06:00 अपराह्न",
        "samvat": "2082",
        "festivals": ["गुरु पूर्णिमा"] if festivals else [],
    }
    return en if lang == "en" else hi

@app.get("/api/panchang")
async def panchang(
    city: str = Query("delhi"), 
    date: str = Query("2025-07-15"), 
    lang: str = Query("en")
):
    try:
        data = get_panchang(city, date, lang)
        return data
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/")
def root():
    return {
        "msg": "PanchangBodh API is running! Example: /api/panchang?city=delhi&date=2025-07-15&lang=en"
    }
