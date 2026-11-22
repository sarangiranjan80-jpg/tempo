from thermoshelter.engine import calculate_envelope, simulate_indoor_temperature

def test_envelope_zero_delta_has_zero_fabric_and_ventilation():
    result = calculate_envelope(40, 3, 1.2, 1.8, 25, 25, .5, 0)
    assert result["fabric_w"] == 0
    assert result["ventilation_w"] == 0

def test_hot_outdoor_air_increases_positive_load():
    result = calculate_envelope(40, 3, 1.2, 1.8, 35, 25, .5, 0)
    assert result["total_w"] > 0

def test_temperature_response_moves_toward_outdoor():
    series = simulate_indoor_temperature([35]*8, 25, 40, 3, 1.2, 1.8, .5)
    assert len(series) == 8
    assert series[-1] > series[0]


def test_design_case_heating_increases_when_outdoor_is_colder():
    from thermoshelter.engine import calculate_design_case
    args = dict(length=8, width=5, wall_height=3, floor_area=40,
                wall_u=1.2, roof_u=.8, floor_u=.7, window_u=2.7,
                window_area=4, door_area=2, indoor_temp=20, ach=.5)
    mild = calculate_design_case(outdoor_temp=5, **args)
    cold = calculate_design_case(outdoor_temp=-15, **args)
    assert cold["heating_w"] > mild["heating_w"]

def test_added_insulation_reduces_wall_u_value():
    from thermoshelter.engine import calculate_design_case
    args = dict(length=8, width=5, wall_height=3, floor_area=40,
                wall_u=1.2, roof_u=.8, floor_u=.7, window_u=2.7,
                window_area=4, door_area=2, indoor_temp=20, outdoor_temp=-10,
                ach=.5)
    base = calculate_design_case(insulation_thickness_mm=0, **args)
    insulated = calculate_design_case(insulation_thickness_mm=100, **args)
    assert insulated["improved_wall_u"] < base["improved_wall_u"]

def test_ladakh_locations_present():
    from thermoshelter.locations import INDIA_CITIES
    assert all(name in INDIA_CITIES for name in ["Leh", "Kargil", "Drass"])

def test_multilayer_assembly_resistance_and_u_value():
    from thermoshelter.advanced_engine import assembly_resistance
    result = assembly_resistance([{"name":"brick","thickness_m":0.20,"k":0.70}])
    assert result["r_total_m2k_w"] > 0.20/0.70
    assert result["u_w_m2k"] == 1 / result["r_total_m2k_w"]

def test_thermal_bridge_increases_heating_load():
    from thermoshelter.advanced_engine import envelope_loads
    base = envelope_loads(areas=[40],u_values=[1.0],delta_t_k=20,ach=0,volume_m3=100)
    bridged = envelope_loads(areas=[40],u_values=[1.0],delta_t_k=20,ach=0,volume_m3=100,
                             bridges=[{"psi_w_mk":0.1,"length_m":30}])
    assert bridged["heating_w"] > base["heating_w"]

def test_transient_wall_returns_hourly_flux():
    from thermoshelter.advanced_engine import transient_wall_response
    result = transient_wall_response([{"thickness_m":0.1,"k":0.5,"rho":1000,"cp":1000}],
                                     t_out_c=0,t_in_c=20,hours=3,dt_seconds=60)
    assert len(result["hourly_inside_heat_flux_w_m2"]) == 3
    assert result["cells"] >= 3

def test_zone_model_and_insulation_optimiser():
    from thermoshelter.advanced_engine import simulate_zone_hourly, optimise_insulation
    sim = simulate_zone_hourly([0,0,0],ua_w_k=100,thermal_capacity_j_k=1e7,setpoint_c=20)
    assert len(sim["indoor_temperature_c"]) == 3
    best, rows = optimise_insulation(base_wall_u=1.2,base_roof_u=.8,wall_area_m2=50,
        roof_area_m2=40,delta_t_k=20,annual_degree_hours=1800,tariff_inr_kwh=8)
    assert best["wall_insulation_mm"] >= 0 and len(rows) > 1
