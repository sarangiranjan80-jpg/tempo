"""Transparent preliminary building heat-transfer engine. SI units throughout."""
from __future__ import annotations
import math
import numpy as np

MATERIALS = {
    "Plaster": {"k": 0.72, "rho": 1600, "cp": 840},
    "Brick masonry": {"k": 0.72, "rho": 1800, "cp": 840},
    "AAC block": {"k": 0.16, "rho": 600, "cp": 1000},
    "Concrete": {"k": 1.70, "rho": 2300, "cp": 880},
    "Stone masonry": {"k": 1.80, "rho": 2200, "cp": 850},
    "Mineral wool": {"k": 0.037, "rho": 45, "cp": 840},
    "EPS": {"k": 0.036, "rho": 20, "cp": 1400},
    "XPS": {"k": 0.030, "rho": 35, "cp": 1450},
    "Timber": {"k": 0.13, "rho": 550, "cp": 1600},
    "Gypsum board": {"k": 0.25, "rho": 800, "cp": 1090},
}

# Indicative preliminary screening temperatures only; replace with project-specific
# ISHRAE/IMD/approved design weather data before engineering design.
CLIMATE_DESIGN = {
    "Leh": {"winter_min_c": -15.0, "summer_max_c": 25.0, "zone": "Cold & sunny / high altitude"},
    "Kargil": {"winter_min_c": -18.0, "summer_max_c": 27.0, "zone": "Cold / high altitude"},
    "Drass": {"winter_min_c": -25.0, "summer_max_c": 22.0, "zone": "Very cold / high altitude"},
    "Diskit (Nubra Valley)": {"winter_min_c": -12.0, "summer_max_c": 30.0, "zone": "Cold desert"},
    "Srinagar": {"winter_min_c": -5.0, "summer_max_c": 32.0, "zone": "Cold"},
    "Shimla": {"winter_min_c": -2.0, "summer_max_c": 27.0, "zone": "Composite / hill"},
    "New Delhi": {"winter_min_c": 4.0, "summer_max_c": 43.0, "zone": "Composite"},
    "Jaipur": {"winter_min_c": 5.0, "summer_max_c": 44.0, "zone": "Hot-dry"},
    "Ahmedabad": {"winter_min_c": 9.0, "summer_max_c": 43.0, "zone": "Hot-dry"},
    "Mumbai": {"winter_min_c": 18.0, "summer_max_c": 35.0, "zone": "Warm-humid"},
    "Chennai": {"winter_min_c": 20.0, "summer_max_c": 38.0, "zone": "Warm-humid"},
    "Kolkata": {"winter_min_c": 11.0, "summer_max_c": 39.0, "zone": "Warm-humid / composite"},
    "Bardhaman": {"winter_min_c": 10.0, "summer_max_c": 40.0, "zone": "Composite"},
    "Bengaluru": {"winter_min_c": 14.0, "summer_max_c": 34.0, "zone": "Moderate"},
    "Hyderabad": {"winter_min_c": 12.0, "summer_max_c": 40.0, "zone": "Composite"},
    "Pune": {"winter_min_c": 9.0, "summer_max_c": 38.0, "zone": "Moderate"},
    "Dehradun": {"winter_min_c": 4.0, "summer_max_c": 38.0, "zone": "Composite"},
    "Guwahati": {"winter_min_c": 8.0, "summer_max_c": 36.0, "zone": "Warm-humid"},
    "Kochi": {"winter_min_c": 22.0, "summer_max_c": 34.0, "zone": "Warm-humid"},
    "Siliguri": {"winter_min_c": 7.0, "summer_max_c": 36.0, "zone": "Composite / humid"},
    "Bhopal": {"winter_min_c": 7.0, "summer_max_c": 42.0, "zone": "Composite"},
    "Lucknow": {"winter_min_c": 5.0, "summer_max_c": 43.0, "zone": "Composite"},
    "Patna": {"winter_min_c": 7.0, "summer_max_c": 42.0, "zone": "Composite"},
    "Bhubaneswar": {"winter_min_c": 15.0, "summer_max_c": 39.0, "zone": "Warm-humid"},
    "Raipur": {"winter_min_c": 8.0, "summer_max_c": 43.0, "zone": "Composite / hot"},
    "Ranchi": {"winter_min_c": 6.0, "summer_max_c": 39.0, "zone": "Moderate / composite"},
    "Dehradun": {"winter_min_c": 4.0, "summer_max_c": 38.0, "zone": "Composite"},
    "Thiruvananthapuram": {"winter_min_c": 22.0, "summer_max_c": 34.0, "zone": "Warm-humid"},
    "Panaji": {"winter_min_c": 20.0, "summer_max_c": 34.0, "zone": "Warm-humid"},
    "Nagpur": {"winter_min_c": 8.0, "summer_max_c": 44.0, "zone": "Composite / hot"},
    "Jodhpur": {"winter_min_c": 5.0, "summer_max_c": 44.0, "zone": "Hot-dry"},
}

R_SI = 0.13
R_SE = 0.04

def assembly_resistance(layers, r_inside=R_SI, r_outside=R_SE):
    """layers: iterable of dicts {name, thickness_m, k, rho?, cp?}."""
    if not layers:
        raise ValueError("An assembly must contain at least one material layer")
    rows, total_r, areal_capacity = [], float(r_inside + r_outside), 0.0
    for layer in layers:
        t, k = float(layer["thickness_m"]), float(layer["k"])
        if t <= 0 or k <= 0:
            raise ValueError("Layer thickness and conductivity must be positive")
        r = t / k
        cap = t * float(layer.get("rho", 0)) * float(layer.get("cp", 0))
        rows.append({"material": layer.get("name", "Layer"), "thickness_m": t, "k_w_mk": k,
                     "r_m2k_w": r, "areal_heat_capacity_j_m2k": cap})
        total_r += r
        areal_capacity += cap
    return {"layers": rows, "r_total_m2k_w": total_r, "u_w_m2k": 1.0 / total_r,
            "areal_heat_capacity_j_m2k": areal_capacity}

def envelope_loads(*, areas, u_values, delta_t_k, ach, volume_m3, internal_gains_w=0,
                   solar_gains_w=0, bridges=None):
    """Signed heat-balance: positive heating required, negative cooling required."""
    bridges = bridges or []
    fabric = sum(float(a) * float(u) * float(delta_t_k) for a, u in zip(areas, u_values))
    ventilation = 0.33 * float(ach) * float(volume_m3) * float(delta_t_k)
    bridge_w = sum(float(b.get("psi_w_mk", 0)) * float(b.get("length_m", 0)) * float(delta_t_k)
                   for b in bridges)
    net = fabric + ventilation + bridge_w - float(solar_gains_w) - float(internal_gains_w)
    return {"fabric_w": fabric, "ventilation_w": ventilation, "thermal_bridge_w": bridge_w,
            "solar_gains_w": float(solar_gains_w), "internal_gains_w": float(internal_gains_w),
            "net_load_w": net, "heating_w": max(0.0, net), "cooling_w": max(0.0, -net)}

def transient_wall_response(layers, t_out_c, t_in_c, hours=48, dt_seconds=60, initial_c=None):
    """1-D explicit finite-volume conduction through layered wall; fixed surface temps.
    Returns hourly inside-face heat flux. Grid is refined by layer and substepped for stability.
    This is a 1-D conduction benchmark, not a whole-building CFD/FEA solver.
    """
    if not layers or hours <= 0 or dt_seconds <= 0:
        raise ValueError("Valid layers, hours and timestep are required")
    # At least 3 cells per layer; use uniform cell size based on thinnest layer.
    dx_target = min(float(x["thickness_m"]) for x in layers) / 3.0
    ks, rhos, cps = [], [], []
    for lay in layers:
        n = max(3, int(math.ceil(float(lay["thickness_m"]) / dx_target)))
        ks.extend([float(lay["k"])] * n); rhos.extend([float(lay.get("rho", 1800))] * n); cps.extend([float(lay.get("cp", 840))] * n)
    # Construct actual cell widths while retaining layer boundaries.
    widths = []
    for lay in layers:
        n = max(3, int(math.ceil(float(lay["thickness_m"]) / dx_target)))
        widths.extend([float(lay["thickness_m"]) / n] * n)
    widths = np.asarray(widths); k=np.asarray(ks); rho=np.asarray(rhos); cp=np.asarray(cps)
    alpha = k/(rho*cp)
    stable_dt = 0.40 * float(np.min(widths**2 / alpha))
    dt = min(float(dt_seconds), stable_dt)
    steps_per_hour = int(math.ceil(3600.0 / dt)); dt = 3600.0 / steps_per_hour
    t = np.full(len(k), float(initial_c if initial_c is not None else (t_out_c+t_in_c)/2))
    hourly_flux=[]; total_steps=int(hours*steps_per_hour); out=float(t_out_c); inside=float(t_in_c)
    # Surface film resistances are applied as boundary conductances.
    for step in range(total_steps):
        q = np.zeros(len(t)+1)
        # Heat flux positive from outside toward inside.
        q[0] = (out - t[0]) / (0.04 + widths[0]/(2*k[0]))
        for j in range(1,len(t)):
            resistance = widths[j-1]/(2*k[j-1]) + widths[j]/(2*k[j])
            q[j] = (t[j-1]-t[j]) / resistance
        q[-1] = (t[-1]-inside) / (widths[-1]/(2*k[-1]) + 0.13)
        t += (q[:-1]-q[1:]) * dt/(rho*cp*widths)
        if (step+1) % steps_per_hour == 0:
            hourly_flux.append(float(q[-1]))
    return {"hourly_inside_heat_flux_w_m2": hourly_flux, "final_cell_temperatures_c": t.tolist(),
            "time_step_seconds": dt, "cells": len(t)}

def simulate_zone_hourly(outdoor_c, *, ua_w_k, thermal_capacity_j_k, setpoint_c,
                         internal_gains_w=0.0, solar_gains_w=None, initial_c=None,
                         heating_cop=1.0, cooling_cop=1.0):
    """Hourly 1R-1C zone model with ideal setpoint HVAC; returns thermal/electric energy."""
    out=np.asarray(outdoor_c,dtype=float)
    if out.ndim != 1 or len(out)==0 or ua_w_k<=0 or thermal_capacity_j_k<=0:
        raise ValueError("Outdoor series, UA and thermal capacity must be positive")
    solar=np.zeros_like(out) if solar_gains_w is None else np.asarray(solar_gains_w,dtype=float)
    if solar.shape != out.shape: raise ValueError("Solar gains series must match outdoor series")
    temp=float(setpoint_c if initial_c is None else initial_c); temps=[]; heat=[]; cool=[]
    dt=3600.0
    for tout, sol in zip(out,solar):
        free = temp + (ua_w_k*(tout-temp)+float(internal_gains_w)+sol)*dt/thermal_capacity_j_k
        h=max(0.0,(float(setpoint_c)-free)*thermal_capacity_j_k/dt)
        c=max(0.0,(free-float(setpoint_c))*thermal_capacity_j_k/dt)
        temp=free+h*dt/thermal_capacity_j_k-c*dt/thermal_capacity_j_k
        temps.append(temp); heat.append(h); cool.append(c)
    heat_kwh=sum(heat)/1000; cool_kwh=sum(cool)/1000
    return {"indoor_temperature_c":temps,"heating_load_w":heat,"cooling_load_w":cool,
            "heating_thermal_kwh":heat_kwh,"cooling_thermal_kwh":cool_kwh,
            "electricity_kwh":heat_kwh/max(heating_cop,1e-9)+cool_kwh/max(cooling_cop,1e-9)}

def optimise_insulation(*, base_wall_u, base_roof_u, wall_area_m2, roof_area_m2,
                        delta_t_k, annual_degree_hours, tariff_inr_kwh, heating_cop=1.0,
                        cost_wall_inr_m2_per_m=12000, cost_roof_inr_m2_per_m=10000,
                        k_insulation=0.037, thickness_options_mm=(0,20,40,60,80,100,120,150,180,200)):
    """Transparent discrete screening: annual conductive savings vs installed insulation cost.
    Objective = simple payback; not lifecycle optimisation or calibrated annual energy.
    """
    candidates=[]
    for tw in thickness_options_mm:
        for tr in thickness_options_mm:
            uw=1/(1/base_wall_u+(tw/1000)/k_insulation)
            ur=1/(1/base_roof_u+(tr/1000)/k_insulation)
            saved_w=((base_wall_u-uw)*wall_area_m2+(base_roof_u-ur)*roof_area_m2)*abs(delta_t_k)
            saved_kwh=saved_w*annual_degree_hours/1000/max(heating_cop,1e-9)
            capex=wall_area_m2*(tw/1000)*cost_wall_inr_m2_per_m+roof_area_m2*(tr/1000)*cost_roof_inr_m2_per_m
            annual_saving=saved_kwh*tariff_inr_kwh
            payback=capex/annual_saving if annual_saving>0 else (0.0 if capex==0 else float('inf'))
            candidates.append({"wall_insulation_mm":tw,"roof_insulation_mm":tr,"wall_u":uw,"roof_u":ur,
                               "estimated_saving_kwh_year":saved_kwh,"estimated_annual_saving_inr":annual_saving,
                               "estimated_capex_inr":capex,"simple_payback_years":payback})
    # Lowest simple payback, excluding zero-cost baseline unless all savings are zero.
    feasible=[x for x in candidates if x["estimated_capex_inr"]>0 and math.isfinite(x["simple_payback_years"])]
    best=min(feasible,key=lambda x:x["simple_payback_years"]) if feasible else candidates[0]
    return best, sorted(candidates,key=lambda x:x["simple_payback_years"])
