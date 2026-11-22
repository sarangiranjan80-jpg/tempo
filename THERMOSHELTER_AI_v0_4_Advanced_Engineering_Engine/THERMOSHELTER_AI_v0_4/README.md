# THERMOSHELTER AI — Development build 0.2

A location-aware India climate and shelter thermal-screening dashboard.

## What's new
- Colourful Streamlit dashboard with an India city network shown as 3D weather columns.
- 27 selectable Indian cities, including Bardhaman.
- Live current conditions, hourly data and a 7-day forecast feed from Open-Meteo.
- Local climate/weather news search using GDELT DOC 2.0.
- Engineering workbench: simplified envelope heat transfer, ventilation load, solar screening, indoor temperature response, insulation screening and indicative assembly comparison.
- Cached API calls, timeout/error handling, tests and deployment notes.

## Run on Windows
Use Python 3.11 or 3.12. Open PowerShell in this folder:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m pytest -v
streamlit run app.py
```

Open `http://localhost:8501`.

If PowerShell blocks activation:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Data connectors
- Open-Meteo Forecast API: https://open-meteo.com/ . No API key is required for the free non-commercial tier. Weather data attribution is included in the UI. Check current terms and licence before public/commercial use.
- GDELT DOC 2.0: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/ . No API key. News results are third-party reporting, not official warnings. Respect provider rate limits.
- Network access is required for live data. If either connector is unreachable, the app should still show a usable engineering workbench (weather can be entered manually).

## Current scope and limitations
This is a development release, not a production-certified application.
- The map is a 3D city-column visualisation, not a complete state-boundary GIS model or a fully clickable terrain mesh. Select a city in the sidebar.
- City coordinates are a starter catalogue, not a complete national weather-station inventory.
- Weather forecast is not a long-term climate normal. Historical and climate-projection feeds should be added as separate, explicitly labelled modules.
- News search is location-keyword based; it is not an official alert service and may include irrelevant or duplicate coverage.
- The engineering model is a simplified screening tool. It assumes square floor plan, four opaque walls, simplified ventilation, fixed effective thermal capacity and approximate solar gain. It is not a detailed building energy model.
- No moisture transport, thermal bridges, glazing optics, detailed solar geometry, ground coupling, PCM enthalpy model or experimental validation yet.
- No ANSYS solver automation or validated ANSYS comparison yet. That is a later integration stage.

## Before production deployment
1. Decide intended commercial/non-commercial use and obtain appropriate weather/news data rights.
2. Add secure authentication/authorisation, secrets management, HTTPS, rate limiting and abuse controls.
3. Add persistent database for cases, users, inputs, model versions and outputs.
4. Add structured logs, monitoring, exception tracking, backups and deployment health checks.
5. Add data freshness indicators, provider attribution and source links.
6. Add integration tests, CI pipeline, dependency pinning/SBOM and security review.
7. Add engineering verification against analytical benchmarks and independent validation datasets.
8. Add a proper GIS layer with licensed India state boundaries and map interaction after choosing a map stack.

## Suggested next development milestones
- v0.3: clickable state/city GIS map, full hourly forecast charts, AQI and historical climate normals.
- v0.4: multi-layer transient wall/roof conduction, glazing, solar geometry and moisture-aware assemblies.
- v0.5: NSGA-II multi-objective design optimisation with cost/comfort/energy Pareto front.
- v0.6: ANSYS CSV import/export validation centre and mesh/time-step comparison workflow.
- v1.0: deployment hardening, database, audit trail, monitoring and documented validation.


## v0.3 — Thermal Design Calculator

The dedicated **Thermal Design Calculator** workspace provides a single form for:
- project location (including Leh, Kargil, Drass and Diskit in Ladakh);
- rectangular building geometry (floor/roof area derived from length × width);
- wall, roof, floor, glazing and door inputs;
- indoor/outdoor design temperatures, ACH and internal gains;
- roof solar screening assumptions and added wall insulation;
- heating/cooling screening loads, component breakdown, revised wall U-value,
  an equivalent-full-load-hours energy-cost scenario, and CSV export.

The ANSYS validation workspace is a preparation/roadmap panel only. It does not
launch ANSYS, create a solver model, or claim validation. The current analytical
model is simplified: floor heat transfer uses the outdoor design temperature as
a boundary, the door U-value is approximated by the wall U-value, solar gain is
a roof-only screening term, and annual energy is an equivalent-full-load-hours
scenario rather than a dynamic annual simulation.

## v0.4 Advanced engineering calculation engine

The Thermal Design Calculator now includes:

- **Multilayer constructions:** editable wall, roof and floor layers. Layer resistance is `R = thickness / conductivity`; assembly U-value includes inside/outside surface-film resistances (default 0.13 and 0.04 m²K/W).
- **Openings and bridges:** explicit whole-window and door U-values, glazing area and SHGC, plus aggregate linear bridge loss `Q = Ψ × L × ΔT`.
- **Indian climate design presets:** editable winter/summer screening temperatures for the city catalogue, including Leh, Kargil, Drass and Diskit. These are illustrative defaults only; replace with approved local design weather (e.g. applicable ISHRAE/IMD data) for actual design.
- **Transient conduction:** explicit 1-D finite-volume multilayer wall step response with stability-limited internal timestep and hourly inside-face heat flux.
- **Thermal mass / zone response:** reduced-order 1R-1C hourly zone model with a seven-day synthetic design stress profile, ideal setpoint heating/cooling and HVAC COP.
- **Optimisation:** discrete wall/roof insulation thickness screening using annual degree-hour assumptions, indicative cost coefficients, annual energy saving and simple payback.

### Engineering limitations

This is an auditable educational/preliminary engineering model, not a certified HVAC sizing, building-code compliance, moisture, condensation, hygrothermal, whole-building annual simulation or life-safety tool. The climate presets are not percentile design weather. The floor currently uses the same outdoor design boundary as the envelope screening model. Thermal bridges are an aggregate user input, not 2-D junction calculations. Transient conduction is 1-D with fixed boundary temperatures. The zone model uses synthetic hourly weather and ideal setpoint control. The optimiser uses assumed degree-hours and cost coefficients; it is not lifecycle-cost or multi-objective optimisation. Verify with authoritative weather, project material data, applicable standards and a qualified engineer before construction.

ANSYS is deliberately not connected in this release. The next phase is matched-geometry/boundary-condition export and Python-versus-ANSYS verification after the Python engine has been reviewed.
