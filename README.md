# PanchangBodh API – Quick Start (Render)

1. Upload project files (main.py, requirements.txt, Procfile) to a folder.
2. ZIP the folder and upload to Render as a new Web Service.
3. Build command: pip install -r requirements.txt
4. Start command: uvicorn main:app --host 0.0.0.0 --port 10000
5. After deploy, test: https://YOUR-RENDER-URL/api/panchang?city=delhi&date=2025-07-15&lang=en
