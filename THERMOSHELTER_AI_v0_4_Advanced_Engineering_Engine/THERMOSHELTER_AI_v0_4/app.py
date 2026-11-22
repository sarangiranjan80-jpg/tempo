import numpy as np
import streamlit as st
import pandas as pd
import plotly.express as px
import pydeck as pdk
from thermoshelter.locations import INDIA_CITIES
from thermoshelter.weather import get_weather, weather_summary
from thermoshelter.news import get_local_news
from thermoshelter.engine import calculate_envelope, simulate_indoor_temperature

st.set_page_config(page_title="THERMOSHELTER AI", page_icon="🌡️", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;600;700&display=swap');
html, body, [class*="css"] {font-family:'DM Sans',sans-serif;}
.stApp {background:linear-gradient(135deg,#071426 0%,#0b1d34 48%,#102b3c 100%); color:#edf6ff;}
h1,h2,h3 {font-family:'Space Grotesk',sans-serif;color:#f5fbff;}
[data-testid="stMetric"] {background:linear-gradient(145deg,rgba(27,61,87,.88),rgba(17,39,62,.92));border:1px solid rgba(110,210,255,.20);padding:16px;border-radius:16px;}
[data-testid="stSidebar"] {background:#0a192b;}
.stButton>button {border-radius:12px;border:1px solid #39c6d8;background:linear-gradient(90deg,#087f8c,#13a6a6);color:white;font-weight:700;}
div[data-testid="stAlert"] {border-radius:14px;}
.card {background:linear-gradient(145deg,rgba(20,52,77,.9),rgba(13,34,55,.95));border:1px solid rgba(97,193,221,.22);border-radius:18px;padding:18px;margin-bottom:10px;}
.muted {color:#9db8cb;font-size:.88rem;}
.kicker {color:#5de0d0;text-transform:uppercase;letter-spacing:2px;font-size:.72rem;font-weight:800;}
</style>
""", unsafe_allow_html=True)


def render_design_calculator():
    from thermoshelter.advanced_engine import (MATERIALS, CLIMATE_DESIGN, assembly_resistance,
        envelope_loads, transient_wall_response, simulate_zone_hourly, optimise_insulation)
    st.markdown('<div class="kicker">ENGINEERING WORKFLOW • LAYERED PHYSICS • DYNAMIC RESPONSE</div>', unsafe_allow_html=True)
    st.title("Advanced Thermal Design & Calculation Engine")
    st.write("One guided input page for construction layers, thermal bridges, openings, climate design cases, transient response and insulation screening optimisation.")
    st.info("Engineering status: transparent analytical / reduced-order model. Climate values are indicative screening defaults, not certified ISHRAE/IMD design weather. Use project-approved weather and verify against applicable codes before real construction. ANSYS is intentionally deferred until this Python engine is tested.")

    with st.form("advanced_thermal_design_inputs"):
        st.markdown("### 1 · Site and climate design case")
        c1,c2,c3 = st.columns(3)
        with c1:
            site_name = st.selectbox("Project location", list(INDIA_CITIES.keys()), index=list(INDIA_CITIES.keys()).index("Leh"))
            site = INDIA_CITIES[site_name]
        with c2:
            climate = CLIMATE_DESIGN.get(site_name, {"winter_min_c": 8.0, "summer_max_c": 38.0, "zone": "Indicative regional default"})
            st.text_input("Climate classification (screening)", climate["zone"], disabled=True)
        with c3:
            climate_case = st.selectbox("Design season", ["Winter heating", "Summer cooling"])
        default_out = climate["winter_min_c"] if climate_case == "Winter heating" else climate["summer_max_c"]
        st.caption(f"{site['state']} · {site['lat']:.4f}°N, {site['lon']:.4f}°E · Default design dry-bulb {default_out:.1f} °C (editable).")

        st.markdown("### 2 · Building geometry and operating conditions")
        g1,g2,g3,g4 = st.columns(4)
        with g1: length = st.number_input("Length (m)", 1.0, 200.0, 8.0, .5)
        with g2: width = st.number_input("Width (m)", 1.0, 200.0, 5.0, .5)
        with g3: height = st.number_input("Wall height (m)", 2.0, 15.0, 3.0, .1)
        with g4: orientation = st.selectbox("Main glazed façade", ["North", "East", "South", "West"])
        floor_area = length * width; volume = floor_area * height
        st.caption(f"Floor/roof area {floor_area:.1f} m² · Internal volume {volume:.1f} m³ · Gross wall area {2*(length+width)*height:.1f} m²")
        o1,o2,o3,o4 = st.columns(4)
        with o1: indoor_setpoint = st.number_input("Indoor setpoint (°C)", 10.0, 32.0, 20.0 if climate_case.startswith("Winter") else 26.0, .5)
        with o2: outdoor_design = st.number_input("Outdoor design temperature (°C)", -40.0, 55.0, float(default_out), .5)
        with o3: ach = st.number_input("Ventilation / infiltration (ACH)", 0.0, 10.0, .5, .1)
        with o4: internal_gains = st.number_input("Internal gains (W)", 0.0, 50000.0, 300.0, 50.0)

        def layer_inputs(label, defaults):
            st.markdown(f"**{label} construction — outside to inside**")
            layers=[]
            for idx, (mat_default, thick_default) in enumerate(defaults, 1):
                a,b = st.columns([2,1])
                with a: mat = st.selectbox(f"{label} layer {idx} material", list(MATERIALS), index=list(MATERIALS).index(mat_default), key=f"{label}_{idx}_mat")
                with b: thick = st.number_input(f"Layer {idx} thickness (mm)", 1.0, 1000.0, float(thick_default), 5.0, key=f"{label}_{idx}_thick")
                prop=MATERIALS[mat]
                layers.append({"name":mat,"thickness_m":thick/1000,"k":prop["k"],"rho":prop["rho"],"cp":prop["cp"]})
            return layers

        st.markdown("### 3 · Material-by-material multilayer assemblies")
        st.caption("Thermal resistance is calculated as R = thickness / conductivity, with inside/outside surface-film resistances included.")
        wall_layers = layer_inputs("Wall", [("Plaster",15),("Brick masonry",230),("Plaster",15)])
        roof_layers = layer_inputs("Roof", [("Concrete",120),("EPS",60),("Concrete",40)])
        floor_layers = layer_inputs("Floor", [("Concrete",120),("Tile",15)] if "Tile" in MATERIALS else [("Concrete",120),("Brick masonry",20)])

        st.markdown("### 4 · Openings and thermal bridges")
        a,b,c,d = st.columns(4)
        with a: window_area = st.number_input("Window / glazing area (m²)", 0.0, 1000.0, 4.0, .5)
        with b: window_u = st.number_input("Whole-window U-value (W/m²K)", .3, 8.0, 2.7, .1)
        with c: window_shgc = st.slider("Window SHGC", 0.0, 1.0, .45, .05)
        with d: door_area = st.number_input("External door area (m²)", 0.0, 500.0, 2.0, .5)
        a,b,c = st.columns(3)
        with a: door_u = st.number_input("Door U-value (W/m²K)", .3, 8.0, 2.0, .1)
        with b: psi = st.number_input("Aggregate bridge Ψ-value (W/mK)", 0.0, 5.0, .08, .01, help="Equivalent linear transmittance; enter a project-derived value if available.")
        with c: bridge_length = st.number_input("Total bridge length (m)", 0.0, 2000.0, 35.0, 1.0)
        st.caption("Thermal bridges are modelled as Ψ × length × ΔT. This is a user-supplied aggregate estimate; junction-specific 2-D/3-D calculations remain future validation work.")

        st.markdown("### 5 · Solar and dynamic thermal-mass assumptions")
        s1,s2,s3,s4 = st.columns(4)
        with s1: solar_irradiance = st.number_input("Peak incident façade solar (W/m²)", 0.0, 1200.0, 350.0, 25.0)
        with s2: shading_factor = st.slider("Solar access after shading", 0.0, 1.0, .55, .05)
        with s3: mass_factor = st.selectbox("Effective internal thermal mass", ["Light", "Medium", "Heavy"], index=1)
        with s4: tariff = st.number_input("Electricity tariff (₹/kWh)", 0.0, 100.0, 8.0, .5)
        cop_h = st.number_input("Heating system COP", 0.5, 8.0, 1.0, .1)
        cop_c = st.number_input("Cooling system COP", 0.5, 8.0, 3.0, .1)
        submitted = st.form_submit_button("⚙️ RUN FULL THERMAL CALCULATION", use_container_width=True)

    if not submitted:
        st.warning("Enter or review the values above, then run the calculation. All five requested engineering modules execute from this single input page.")
        return

    wall=assembly_resistance(wall_layers); roof=assembly_resistance(roof_layers); floor=assembly_resistance(floor_layers)
    gross_wall=2*(length+width)*height
    opaque_wall=max(0.0,gross_wall-window_area-door_area)
    if window_area+door_area > gross_wall:
        st.error("Window plus door area exceeds gross wall area. Correct the geometry inputs."); return
    wall_area_each=opaque_wall/4.0
    # Simplified aggregate solar term on glazing; façade orientation is recorded for later hourly solar model.
    orientation_factor={"North":0.45,"East":0.80,"South":0.65,"West":0.85}[orientation]
    solar_gain=window_area*solar_irradiance*window_shgc*shading_factor*orientation_factor
    delta=indoor_setpoint-outdoor_design
    areas=[opaque_wall,floor_area,floor_area,window_area,door_area]
    uvals=[wall["u_w_m2k"],roof["u_w_m2k"],floor["u_w_m2k"],window_u,door_u]
    bridges=[{"psi_w_mk":psi,"length_m":bridge_length}]
    loads=envelope_loads(areas=areas,u_values=uvals,delta_t_k=delta,ach=ach,volume_m3=volume,
                         internal_gains_w=internal_gains,solar_gains_w=solar_gain,bridges=bridges)
    st.markdown("---\n## 6 · Engineering results")
    m1,m2,m3,m4=st.columns(4)
    m1.metric("Heating design load",f"{loads['heating_w']:,.0f} W")
    m2.metric("Cooling design load",f"{loads['cooling_w']:,.0f} W")
    m3.metric("Wall U-value",f"{wall['u_w_m2k']:.3f} W/m²K")
    m4.metric("Roof U-value",f"{roof['u_w_m2k']:.3f} W/m²K")

    st.markdown("### Multilayer thermal-resistance schedule")
    for name, assembly in [("Wall",wall),("Roof",roof),("Floor",floor)]:
        st.markdown(f"**{name} — total R = {assembly['r_total_m2k_w']:.3f} m²K/W · U = {assembly['u_w_m2k']:.3f} W/m²K**")
        st.dataframe(pd.DataFrame(assembly["layers"]), use_container_width=True, hide_index=True)

    st.markdown("### Heat-loss / gain components")
    comp=pd.DataFrame([
        {"Component":"Opaque wall", "Signed load (W)":opaque_wall*wall["u_w_m2k"]*delta},
        {"Component":"Roof", "Signed load (W)":floor_area*roof["u_w_m2k"]*delta},
        {"Component":"Floor (same outdoor boundary approximation)", "Signed load (W)":floor_area*floor["u_w_m2k"]*delta},
        {"Component":"Windows", "Signed load (W)":window_area*window_u*delta},
        {"Component":"External doors", "Signed load (W)":door_area*door_u*delta},
        {"Component":"Ventilation", "Signed load (W)":loads["ventilation_w"]},
        {"Component":"Thermal bridges", "Signed load (W)":loads["thermal_bridge_w"]},
        {"Component":"Solar + internal gains", "Signed load (W)":-solar_gain-internal_gains},
    ])
    st.dataframe(comp,use_container_width=True,hide_index=True)
    fig=px.bar(comp,x="Component",y="Signed load (W)",color="Signed load (W)",color_continuous_scale="RdYlBu_r",template="plotly_dark")
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",xaxis_tickangle=-25)
    st.plotly_chart(fig,use_container_width=True)

    st.markdown("### 7 · Transient 1-D conduction through the multilayer wall")
    transient=transient_wall_response(wall_layers,t_out_c=outdoor_design,t_in_c=indoor_setpoint,hours=48,dt_seconds=60)
    tf=pd.DataFrame({"Hour":range(1,len(transient["hourly_inside_heat_flux_w_m2"])+1),"Inside-face heat flux (W/m²)":transient["hourly_inside_heat_flux_w_m2"]})
    st.line_chart(tf.set_index("Hour"))
    st.caption(f"Finite-volume cells: {transient['cells']} · stable internal timestep: {transient['time_step_seconds']:.2f} s · 48 h step response. Fixed boundary temperatures; no moisture or 2-D junction effects.")

    st.markdown("### 8 · Dynamic indoor temperature and hourly HVAC demand")
    # Synthetic 7-day design stress profile spanning the selected season's daily range.
    swing=8.0
    phase=np.arange(168)*2*np.pi/24-np.pi/2
    outdoor_series=outdoor_design + (swing/2)*(1+np.sin(phase)) if climate_case.startswith("Winter") else outdoor_design-(swing/2)*(1+np.sin(phase))
    total_ua=sum(a*u for a,u in zip(areas,uvals))+0.33*ach*volume+psi*bridge_length
    mass_multiplier={"Light":60000,"Medium":120000,"Heavy":200000}[mass_factor]
    thermal_cap=max(1.0,volume*mass_multiplier)
    solar_series=np.maximum(0,np.sin((np.arange(168)%24-6)*np.pi/12))*solar_gain
    dyn=simulate_zone_hourly(outdoor_series,ua_w_k=max(.1,total_ua),thermal_capacity_j_k=thermal_cap,
        setpoint_c=indoor_setpoint,internal_gains_w=internal_gains,solar_gains_w=solar_series,
        heating_cop=cop_h,cooling_cop=cop_c)
    d1,d2,d3=st.columns(3)
    d1.metric("7-day heating thermal energy",f"{dyn['heating_thermal_kwh']:.1f} kWh")
    d2.metric("7-day cooling thermal energy",f"{dyn['cooling_thermal_kwh']:.1f} kWh")
    d3.metric("7-day HVAC electricity",f"{dyn['electricity_kwh']:.1f} kWh")
    ddf=pd.DataFrame({"Hour":range(1,169),"Outdoor temperature (°C)":outdoor_series,"Indoor temperature (°C)":dyn["indoor_temperature_c"],"Heating load (W)":dyn["heating_load_w"],"Cooling load (W)":dyn["cooling_load_w"]})
    st.line_chart(ddf.set_index("Hour")[["Outdoor temperature (°C)","Indoor temperature (°C)"]])
    st.caption("Reduced-order 1R-1C zone model with ideal setpoint control and a synthetic repeating 24-hour design stress profile. It is not an annual calibrated energy model.")

    st.markdown("### 9 · Heating / cooling demand optimisation")
    opt_best,opt_all=optimise_insulation(base_wall_u=wall["u_w_m2k"],base_roof_u=roof["u_w_m2k"],wall_area_m2=opaque_wall,
        roof_area_m2=floor_area,delta_t_k=abs(delta),annual_degree_hours=1800 if climate_case.startswith("Winter") else 1200,
        tariff_inr_kwh=tariff,heating_cop=cop_h if climate_case.startswith("Winter") else cop_c,
        k_insulation=0.037)
    q1,q2,q3,q4=st.columns(4)
    q1.metric("Suggested wall insulation",f"{opt_best['wall_insulation_mm']} mm")
    q2.metric("Suggested roof insulation",f"{opt_best['roof_insulation_mm']} mm")
    q3.metric("Screened annual saving",f"₹{opt_best['estimated_annual_saving_inr']:,.0f}")
    q4.metric("Simple payback",f"{opt_best['simple_payback_years']:.1f} y" if np.isfinite(opt_best['simple_payback_years']) else "N/A")
    st.dataframe(pd.DataFrame(opt_all[:15]),use_container_width=True,hide_index=True)
    st.caption("Discrete screening optimisation of wall/roof insulation thickness. Uses assumed annual degree-hours and indicative material cost coefficients; validate costs, weather, moisture, embodied carbon and lifecycle assumptions before selection.")

    st.markdown("### 10 · Export calculation record")
    record={"site":site_name,"state":site["state"],"design_season":climate_case,"outdoor_design_c":outdoor_design,
        "indoor_setpoint_c":indoor_setpoint,"floor_area_m2":floor_area,"volume_m3":volume,
        "wall_r_m2k_w":wall["r_total_m2k_w"],"wall_u_w_m2k":wall["u_w_m2k"],
        "roof_r_m2k_w":roof["r_total_m2k_w"],"roof_u_w_m2k":roof["u_w_m2k"],
        "floor_u_w_m2k":floor["u_w_m2k"],"window_u_w_m2k":window_u,"door_u_w_m2k":door_u,
        "bridge_psi_w_mk":psi,"bridge_length_m":bridge_length,"glazed_facade_orientation":orientation,"heating_design_w":loads["heating_w"],
        "cooling_design_w":loads["cooling_w"],"transient_cells":transient["cells"],
        "dynamic_7day_hvac_electricity_kwh":dyn["electricity_kwh"],
        "optimised_wall_insulation_mm":opt_best["wall_insulation_mm"],"optimised_roof_insulation_mm":opt_best["roof_insulation_mm"]}
    st.download_button("⬇ Download full calculation summary (CSV)",pd.DataFrame([record]).to_csv(index=False).encode(),"thermoshelter_advanced_calculation.csv","text/csv")
    with st.expander("ANSYS integration — next phase after Python engine verification"):
        st.info("ANSYS is not connected or executed by this version. This calculation record is the baseline for the later matched-boundary-condition model.")
        st.markdown("1. Export layer geometry, k, density, specific heat, boundary films and temperatures.\n2. Create matching steady-state and transient wall/roof cases in ANSYS Mechanical or Fluent.\n3. Compare heat flux, interface temperatures and time histories.\n4. Report MAE, RMSE and percentage error; archive mesh, solver and convergence settings.")

# Navigation: one dedicated calculator page alongside the existing climate dashboard.
with st.sidebar:
    st.markdown("---")
    page = st.radio("WORKSPACE", ["Climate Dashboard", "Thermal Design Calculator"], index=0)

if page == "Thermal Design Calculator":
    render_design_calculator()
else:

    st.markdown('<div class="kicker">INDIA CLIMATE • THERMAL ENGINEERING • DECISION INTELLIGENCE</div>', unsafe_allow_html=True)
    st.title("THERMOSHELTER AI")
    st.caption("Location-aware shelter design and thermal performance intelligence")

    with st.sidebar:
        st.markdown("## 🧭 Mission control")
        city_names = list(INDIA_CITIES.keys())
        selected_city = st.selectbox("Select a location in India", city_names, index=city_names.index("Bardhaman") if "Bardhaman" in city_names else 0)
        city = INDIA_CITIES[selected_city]
        st.markdown("---")
        st.markdown("### 🏗️ Engineering case")
        analysis = st.selectbox("What do you want to analyse?", [
            "Thermal comfort & indoor temperature", "Envelope heat gain / loss",
            "Insulation thickness screening", "Material and U-value comparison"
        ])
        area = st.number_input("Shelter floor area (m²)", 5.0, 5000.0, 40.0, 5.0)
        height = st.number_input("Indoor height (m)", 2.0, 8.0, 3.0, .1)
        wall_u = st.slider("Wall U-value (W/m²K)", .1, 4.0, 1.2, .05)
        roof_u = st.slider("Roof U-value (W/m²K)", .1, 5.0, 1.8, .05)
        ventilation = st.slider("Air changes per hour (ACH)", 0.0, 5.0, .5, .1)
        indoor_setpoint = st.slider("Target indoor temperature (°C)", 18, 32, 26)
        st.markdown("---")
        refresh = st.button("↻ Refresh live data", use_container_width=True)

    lat, lon = city["lat"], city["lon"]
    weather = get_weather(lat, lon, refresh=refresh)
    summary = weather_summary(weather)
    news = get_local_news(selected_city, city["state"], refresh=refresh)

    # Hero and live conditions
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🌡️ Outdoor temperature", f'{summary["temperature"]:.1f} °C' if summary["temperature"] is not None else "Unavailable")
    c2.metric("💧 Relative humidity", f'{summary["humidity"]:.0f}%' if summary["humidity"] is not None else "Unavailable")
    c3.metric("🌬️ Wind speed", f'{summary["wind"]:.1f} km/h' if summary["wind"] is not None else "Unavailable")
    c4.metric("☀️ UV index", f'{summary["uv"]:.1f}' if summary["uv"] is not None else "Unavailable")

    left, right = st.columns([1.55, 1], gap="large")
    with left:
        st.markdown("### 🌏 India climate explorer")
        st.markdown('<div class="muted">3D weather columns show the selected city network. Choose any city from the map legend or the location selector.</div>', unsafe_allow_html=True)
        map_rows = []
        for name, loc in INDIA_CITIES.items():
            map_rows.append({"city": name, "state": loc["state"], "lat": loc["lat"], "lon": loc["lon"],
                             "elevation": 15000 if name == selected_city else 6000,
                             "radius": 8500 if name == selected_city else 4500,
                             "color": [38, 220, 199, 230] if name == selected_city else [73, 153, 235, 180]})
        map_df = pd.DataFrame(map_rows)
        layer = pdk.Layer("ColumnLayer", data=map_df, get_position="[lon, lat]", get_elevation="elevation",
                          elevation_scale=1, radius=map_df["radius"].tolist(), get_fill_color="color",
                          pickable=True, auto_highlight=True, extruded=True)
        labels = pdk.Layer("TextLayer", data=map_df, get_position="[lon, lat]", get_text="city",
                           get_size=13, get_color=[235, 246, 255, 230], get_alignment_baseline="'bottom'",
                           get_pixel_offset=[0, -12], pickable=True)
        view = pdk.ViewState(latitude=22.8, longitude=79.0, zoom=3.2, pitch=48, bearing=-8)
        st.pydeck_chart(pdk.Deck(layers=[layer, labels], initial_view_state=view,
                                 tooltip={"text": "{city}, {state}"}), use_container_width=True)
        st.caption(f"Selected site: **{selected_city}, {city['state']}** · {lat:.3f}°N, {lon:.3f}°E")

    with right:
        st.markdown("### 🛰️ Local weather & climate feed")
        if weather.get("error"):
            st.warning(f"Weather service unavailable: {weather['error']}")
        else:
            st.markdown(f'<div class="card"><div class="kicker">CURRENT CONDITIONS · {selected_city.upper()}</div><h2>{summary["condition"]}</h2><div style="font-size:2.5rem;font-weight:800">{summary["temperature"]:.1f}°C</div><div class="muted">Feels-like weather context · humidity {summary["humidity"]:.0f}% · wind {summary["wind"]:.1f} km/h</div></div>', unsafe_allow_html=True)
            st.caption("Weather data by Open-Meteo · CC BY 4.0")
        st.markdown("### 📰 Local climate & weather news")
        if news:
            for item in news[:5]:
                st.markdown(f"**[{item['title']}]({item['url']})**")
                st.caption(f"{item['source']} · {item['date']}")
        else:
            st.info("No matching local climate headlines returned. Try refresh or check the connection.")

    st.markdown("---")
    st.markdown("## 🧪 Engineering workbench")
    if weather.get("error") or summary["temperature"] is None:
        outdoor_temp = st.number_input("Fallback outdoor temperature (°C)", -10.0, 55.0, 32.0)
    else:
        outdoor_temp = float(summary["temperature"])
    weather_data = weather.get("hourly", {})
    solar_values = weather_data.get("shortwave_radiation", [])
    solar = float(solar_values[0]) if solar_values and solar_values[0] is not None else 0.0

    result = calculate_envelope(area, height, wall_u, roof_u, outdoor_temp, indoor_setpoint, ventilation, solar)
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Envelope heat transfer", f'{result["fabric_w"]:.0f} W')
    r2.metric("Ventilation load", f'{result["ventilation_w"]:.0f} W')
    r3.metric("Indicative solar gain", f'{result["solar_w"]:.0f} W')
    r4.metric("Total sensible load", f'{result["total_w"]:.0f} W')

    if analysis == "Thermal comfort & indoor temperature":
        st.markdown("### Indoor temperature response")
        hours = st.slider("Simulation duration (hours)", 6, 72, 24)
        hourly_temp = weather_data.get("temperature_2m", [])
        outdoor_series = hourly_temp[:hours] if len(hourly_temp) >= hours else [outdoor_temp] * hours
        sim = simulate_indoor_temperature(outdoor_series, indoor_setpoint, area, height, wall_u, roof_u, ventilation)
        chart = pd.DataFrame({"Hour": range(len(sim)), "Outdoor °C": outdoor_series[:len(sim)], "Indoor model °C": sim})
        fig = px.line(chart, x="Hour", y=["Outdoor °C", "Indoor model °C"], template="plotly_dark",
                      color_discrete_sequence=["#ff9f43", "#38d9c8"])
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", legend_title_text="")
        st.plotly_chart(fig, use_container_width=True)
    elif analysis == "Envelope heat gain / loss":
        st.markdown("### Load breakdown")
        fig = px.bar(pd.DataFrame({"Component":["Wall + roof fabric","Ventilation","Solar (simplified)"],
                                   "Load W":[result["fabric_w"],result["ventilation_w"],result["solar_w"]]}),
                     x="Component", y="Load W", color="Component", template="plotly_dark",
                     color_discrete_sequence=["#25c6da","#ff9f43","#b388ff"])
        fig.update_layout(showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
    elif analysis == "Insulation thickness screening":
        st.markdown("### Insulation screening")
        conductivity = st.selectbox("Insulation type", ["Mineral wool", "EPS", "XPS"], index=0)
        k = {"Mineral wool":.037, "EPS":.036, "XPS":.030}[conductivity]
        thickness = st.slider("Insulation thickness (mm)", 0, 250, 80, 5)
        new_u = 1 / (1 / wall_u + (thickness / 1000) / k)
        st.metric("Estimated revised wall U-value", f"{new_u:.3f} W/m²K", delta=f"{new_u-wall_u:.3f} W/m²K")
        st.caption("Screening calculation only; assumes the entered wall U-value represents the existing assembly.")
    else:
        st.markdown("### Material / envelope comparison")
        choices = st.multiselect("Compare indicative wall U-values", ["Uninsulated masonry","Masonry + 50 mm EPS","Masonry + 100 mm mineral wool"],
                                 default=["Uninsulated masonry","Masonry + 50 mm EPS","Masonry + 100 mm mineral wool"])
        vals = {"Uninsulated masonry":1.8,"Masonry + 50 mm EPS":.55,"Masonry + 100 mm mineral wool":.32}
        if choices:
            fig = px.bar(pd.DataFrame({"Assembly":choices,"U-value":[vals[x] for x in choices]}), x="Assembly",y="U-value",
                         color="Assembly",template="plotly_dark",color_discrete_sequence=["#25c6da","#ff9f43","#b388ff"])
            fig.update_layout(showlegend=False,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig,use_container_width=True)

    st.markdown("---")
    st.markdown("## 🧾 Engineering interpretation")
    st.info(f"For {selected_city}, the current weather input is {outdoor_temp:.1f}°C. The simplified model estimates a sensible load of {result['total_w']:.0f} W for the entered envelope and ventilation assumptions. This is a preliminary screening estimate, not a certified building design or an ANSYS-validated result.")

    with st.expander("Data sources, assumptions & production-readiness notes"):
        st.markdown("""
        - Weather: Open-Meteo forecast API; attribution shown in the interface.
        - News: GDELT DOC 2.0 search results. Headlines are external reporting, not official weather warnings.
        - Map: city-coordinate 3D column visualisation. It is not a cadastral/state-boundary GIS map.
        - Thermal calculations: simplified steady envelope and ventilation loads plus a one-zone lumped-capacitance response.
        - Solar gain is a deliberately simplified screening term; it is not facade-specific solar geometry.
        - No moisture transport, thermal bridges, detailed glazing, wind-pressure infiltration or experimentally validated material database yet.
        - This is a development release, not production-certified software. Before deployment: add authentication, structured logging, rate limiting, persistent storage, monitoring, automated integration tests, security review, and commercial data licences as applicable.
        """)
    st.caption("THERMOSHELTER AI · Development build 0.3 · Engineering decision support, not life-safety certification.")
