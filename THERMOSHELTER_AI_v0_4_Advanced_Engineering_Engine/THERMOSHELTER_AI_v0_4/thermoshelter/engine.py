import numpy as np
import math

def calculate_envelope(area, height, wall_u, roof_u, outdoor_temp, indoor_temp, ach, solar_w_m2=0.0):
    # Screening geometry: square plan, four opaque walls, no explicit window/door deduction.
    side = float(np.sqrt(area))
    wall_area = 4.0 * side * float(height)
    roof_area = float(area)
    delta_t = float(outdoor_temp) - float(indoor_temp)
    fabric = (float(wall_u) * wall_area + float(roof_u) * roof_area) * delta_t
    volume = float(area) * float(height)
    ventilation = 0.33 * float(ach) * volume * delta_t
    # Deliberately conservative placeholder: 10% of incident horizontal solar over roof.
    solar = max(0.0, float(solar_w_m2)) * roof_area * 0.10
    return {"wall_area_m2":wall_area, "roof_area_m2":roof_area,
            "fabric_w":fabric, "ventilation_w":ventilation, "solar_w":solar,
            "total_w":fabric + ventilation + solar}

def simulate_indoor_temperature(outdoor_series, initial_temp, area, height, wall_u, roof_u, ach):
    # Single-zone lumped-capacitance response; assumed effective thermal capacity.
    volume = float(area) * float(height)
    side = float(np.sqrt(area))
    envelope_ua = float(wall_u) * 4 * side * height + float(roof_u) * area
    ventilation_ua = 0.33 * float(ach) * volume
    ua = max(0.1, envelope_ua + ventilation_ua)
    effective_capacity = max(1.0, volume * 1200.0)  # J/K, indicative effective capacity
    dt = 3600.0
    result = [float(initial_temp)]
    for tout in outdoor_series:
        current = result[-1]
        # Exact update for a first-order lumped thermal system; stable for large time constants.
        decay = math.exp(-ua * dt / effective_capacity)
        next_temp = float(tout) + (current - float(tout)) * decay
        result.append(float(next_temp))
    return result[1:]


def calculate_design_case(length, width, wall_height, floor_area,
                          wall_u, roof_u, floor_u, window_u,
                          window_area, door_area, indoor_temp, outdoor_temp,
                          ach, internal_gains=0.0, solar_irradiance=0.0,
                          roof_solar_factor=0.10, insulation_thickness_mm=0.0,
                          insulation_k=0.037):
    """Transparent steady-state screening calculation; not a code-compliance model."""
    length, width, wall_height = map(float, (length, width, wall_height))
    floor_area = float(floor_area)
    volume = floor_area * wall_height
    gross_wall_area = 2.0 * (length + width) * wall_height
    opaque_wall_area = max(0.0, gross_wall_area - float(window_area) - float(door_area))
    dt = float(indoor_temp) - float(outdoor_temp)

    added_r = (float(insulation_thickness_mm) / 1000.0) / max(float(insulation_k), 1e-9)
    improved_wall_u = 1.0 / (1.0 / max(float(wall_u), 1e-9) + added_r)

    wall_w = float(wall_u) * opaque_wall_area * dt
    roof_w = float(roof_u) * floor_area * dt
    # Simplified external-boundary assumption; ground-coupled floor modelling is not included.
    floor_w = float(floor_u) * floor_area * dt
    window_w = float(window_u) * float(window_area) * dt
    door_w = float(wall_u) * float(door_area) * dt
    ventilation_w = 0.33 * float(ach) * volume * dt
    solar_w = max(0.0, float(solar_irradiance)) * floor_area * max(0.0, float(roof_solar_factor))
    internal_gains_w = -abs(float(internal_gains))

    # Positive signed sum means heat must be added to maintain indoor temperature.
    net_heating = wall_w + roof_w + floor_w + window_w + door_w + ventilation_w - solar_w + internal_gains_w
    heating_w = max(0.0, net_heating)
    cooling_w = max(0.0, -net_heating)
    return {
        "volume_m3": volume, "gross_wall_area_m2": gross_wall_area,
        "opaque_wall_area_m2": opaque_wall_area,
        "wall_w": wall_w, "roof_w": roof_w, "floor_w": floor_w,
        "window_w": window_w, "door_w": door_w,
        "ventilation_w": ventilation_w, "solar_w": solar_w,
        "internal_gains_w": internal_gains_w,
        "heating_w": heating_w, "cooling_w": cooling_w,
        "improved_wall_u": improved_wall_u,
        "base_wall_conductance_w_k": float(wall_u) * opaque_wall_area,
        "improved_wall_conductance_w_k": improved_wall_u * opaque_wall_area,
    }
