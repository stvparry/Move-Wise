# MoveWise UK

A Streamlit proof-of-concept that compares a current UK location with a possible destination using free public APIs and user priorities.

## Deploy
1. Create a new GitHub repository.
2. Upload all files from this package to the repository root.
3. In Streamlit Community Cloud choose `streamlit_app.py` as the entry point.
4. No secrets or paid API keys are required for this version.

## Data sources
- Postcodes.io: UK postcode and administrative geography
- OpenStreetMap Nominatim: place/address geocoding
- OpenStreetMap Overpass: nearby amenities
- OSRM: approximate road route distance and duration
- data.police.uk: street-level crime (coverage/methodology varies)

## Important
This is an orientation tool, not a substitute for viewing an area, checking school admissions, conveyancing searches, flood reports, broadband availability, transport timetables or professional property advice. Public APIs can be unavailable, incomplete or rate-limited.
