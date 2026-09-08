
import math


# =============================================================================
# 1. SCENARIO PARAMETERS  (Table 3.2 in thesis)
# =============================================================================

SCENARIO = {
    "interest_rate":            0.047,    # fraction, not %
    "project_lifetime":         15,       # years
    "operating_hours":          8000,     # h/year
    "gas_price":                0.00232,  # EUR/m3(n)
    "biomethane_subsidy":       0.00452,  # EUR/m3(n)
    "min_ch4_fraction":         0.88,     # required CH4 content in biomethane
    "co2_emission_natural_gas": 1.88,     # kg CO2 per m3(n) of natural gas
    "heating_value_natural_gas":9.769,    # kWh/m3(n), higher heating value
    "electricity_price":        0.05,     # EUR/kWh
    "co2_emission_electricity": 0.566,    # kg CO2 per kWh
    "diesel_price":             0.00147,  # EUR/kWh
    "co2_emission_diesel":      0.267,    # kg CO2 per kWh
}


# 2. FINANCIAL HELPERS  (Eq. 3.1 and 3.2)

def present_worth(annual_value,
                  interest_rate=SCENARIO["interest_rate"],
                  project_lifetime=SCENARIO["project_lifetime"]):
    # converts a recurring annual cash flow into its lump-sum present value
    pw_factor = ((1 + interest_rate) ** project_lifetime - 1) / \
                (interest_rate * (1 + interest_rate) ** project_lifetime)
    return annual_value * pw_factor


def annual_worth(present_value,
                 interest_rate=SCENARIO["interest_rate"],
                 project_lifetime=SCENARIO["project_lifetime"]):
    # reverse of present_worth — spreads a lump-sum cost over the project life
    aw_factor = (interest_rate * (1 + interest_rate) ** project_lifetime) / \
                ((1 + interest_rate) ** project_lifetime - 1)
    return present_value * aw_factor



# 3. ELEMENT FUNCTIONS

# Biomass (Eq. 3.3, 3.4)

def biomass_to_biogas_volume(biomass_flow_kg_per_h, biogas_yield_fraction=0.30):
    # how much biogas (m3/h) we get from a given biomass feed
    return biomass_flow_kg_per_h * biogas_yield_fraction


def biomass_annual_cost(biomass_flow_kg_per_h,
                        operating_hours=SCENARIO["operating_hours"],
                        biomass_unit_cost=0.00126):   # EUR/kg
    return biomass_flow_kg_per_h * operating_hours * biomass_unit_cost


# Transport (Eq. 3.5, 3.6, 3.7) 

def transport_fuel_energy(distance_km, biomass_flow_kg_per_h,
                          truck_capacity_kg_per_m3=1.2,
                          operating_hours=SCENARIO["operating_hours"],
                          fuel_use_per_km=0.7):      # kWh/km
    return distance_km * truck_capacity_kg_per_m3 * biomass_flow_kg_per_h \
           * operating_hours * fuel_use_per_km


def transport_co2_emission(fuel_energy_kwh,
                           co2_per_kwh_diesel=SCENARIO["co2_emission_diesel"]):
    return fuel_energy_kwh * co2_per_kwh_diesel


def transport_annual_cost(fuel_energy_kwh, biomass_flow_kg_per_h, distance_km,
                          operating_hours=SCENARIO["operating_hours"],
                          diesel_price=SCENARIO["diesel_price"],
                          handling_cost_per_kg=0.003,
                          distance_cost_per_kg_km=0.001,
                          truck_capacity_kg_per_m3=1.2):
    fuel_cost     = fuel_energy_kwh * diesel_price
    handling_cost = biomass_flow_kg_per_h * operating_hours * handling_cost_per_kg
    distance_cost = biomass_flow_kg_per_h * operating_hours * distance_km \
                    * truck_capacity_kg_per_m3 * distance_cost_per_kg_km
    return fuel_cost + handling_cost + distance_cost


# Digester (Eq. 3.8, 3.9, 3.10, 3.11, 3.12)
def digester_biogas_output(biogas_volumes_m3_per_h, heat_loss_fraction):
    # biogas available after subtracting what's burned for digester heating
    total_biogas = sum(biogas_volumes_m3_per_h)
    return total_biogas * (1 - heat_loss_fraction)


def digester_electricity_use(biogas_volumes_m3_per_h, energy_per_m3,
                              operating_hours=SCENARIO["operating_hours"]):
    return sum(biogas_volumes_m3_per_h) * operating_hours * energy_per_m3


def electricity_co2_emission(electricity_kwh,
                              co2_per_kwh=SCENARIO["co2_emission_electricity"]):
    # generic helper — used by digester, compressor, upgrading plant, etc.
    return electricity_kwh * co2_per_kwh


def digester_annual_opex(capacity, fixed_opex_per_unit, electricity_kwh,
                          electricity_price=SCENARIO["electricity_price"]):
    return capacity * fixed_opex_per_unit + electricity_kwh * electricity_price


def element_capital_cost(capacity, capex_per_unit):
    # same formula applies to digesters, upgrading plants, compressors, etc.
    return capacity * capex_per_unit


# Pre-treatment (Eq. 3.13, 3.14)

def pretreat_electricity_use(biogas_flow_m3_per_h, energy_per_m3,
                              operating_hours=SCENARIO["operating_hours"]):
    return biogas_flow_m3_per_h * operating_hours * energy_per_m3


def pretreat_annual_opex(capacity, fixed_opex_per_m3, biogas_flow_m3_per_h,
                          electricity_kwh,
                          operating_hours=SCENARIO["operating_hours"],
                          electricity_price=SCENARIO["electricity_price"]):
    return capacity * fixed_opex_per_m3 * biogas_flow_m3_per_h \
           * operating_hours + electricity_kwh * electricity_price


#  Compressor (Eq. 3.15, 3.16, 3.17)
def isentropic_compression_energy(inlet_pressure, outlet_pressure,
                                   compressibility=0.9,
                                   gas_constant=8.314, temperature_K=293.15,
                                   molar_mass=0.024,
                                   compression_stages=1, heat_capacity_ratio=1.3):
    # energy in J/kg to compress gas isentropically
    exponent = (heat_capacity_ratio - 1) / (compression_stages * heat_capacity_ratio)
    energy_J_per_kg = (compressibility * gas_constant * temperature_K / molar_mass) \
                      * (compression_stages * heat_capacity_ratio / (heat_capacity_ratio - 1)) \
                      * ((outlet_pressure / inlet_pressure) ** exponent - 1)
    return energy_J_per_kg / 3600   # convert to kWh/kg


def compressor_energy_per_m3(inlet_pressure, outlet_pressure,
                               isentropic_efficiency=0.7,
                               mechanical_efficiency=0.95,
                               electrical_efficiency=0.97,
                               gas_density=1.15):    # kg/m3 at normal conditions
    iso_energy = isentropic_compression_energy(inlet_pressure, outlet_pressure)
    return (iso_energy * gas_density) / \
           (isentropic_efficiency * mechanical_efficiency * electrical_efficiency)


def compressor_annual_energy(gas_flow_m3_per_h, inlet_pressure, outlet_pressure):
    unit_energy = compressor_energy_per_m3(inlet_pressure, outlet_pressure)
    return gas_flow_m3_per_h * unit_energy


# Pipeline (Eq. 3.18, 3.19, 3.20, 3.21, 3.22)

def gas_velocity(volumetric_flow_m3_per_s, pipe_diameter_m):
    cross_section = 0.25 * math.pi * pipe_diameter_m ** 2
    return volumetric_flow_m3_per_s / cross_section


def reynolds_number(gas_velocity_m_per_s, pipe_diameter_m,
                    dynamic_viscosity=1.08e-5):
    return (gas_velocity_m_per_s * pipe_diameter_m) / dynamic_viscosity


def darcy_friction_factor(Re, roughness, pipe_diameter_m, iterations=50):
    if Re < 2300:
        return 64 / Re   # laminar — Hagen-Poiseuille

    # start with Swamee-Jain, then iterate Colebrook-White
    friction = 0.25 / (math.log10(roughness / (3.7 * pipe_diameter_m)
                                   + 5.74 / Re ** 0.9)) ** 2
    for _ in range(iterations):
        rhs = -2 * math.log10(2.51 / (Re * math.sqrt(friction))
                               + roughness / (3.71 * pipe_diameter_m))
        friction = (1 / rhs) ** 2
    return friction


def pipeline_outlet_pressure(inlet_pressure_Pa, pipe_length_m, pipe_diameter_m,
                              volumetric_flow_m3_per_s,
                              normal_density=1.15, temperature_K=293.15,
                              normal_temp_K=273.15, normal_pressure_Pa=1.01325,
                              compressibility=0.9, roughness=1e-5,
                              dynamic_viscosity=1.08e-5):
    velocity  = gas_velocity(volumetric_flow_m3_per_s, pipe_diameter_m)
    Re        = reynolds_number(velocity, pipe_diameter_m, dynamic_viscosity)
    friction  = darcy_friction_factor(Re, roughness, pipe_diameter_m)

    pressure_drop_term = friction * (pipe_length_m / pipe_diameter_m) \
                         * normal_density * velocity ** 2 \
                         * (temperature_K / normal_temp_K) * normal_pressure_Pa \
                         * compressibility

    outlet_sq = inlet_pressure_Pa ** 2 - pressure_drop_term
    if outlet_sq < 0:
        raise ValueError(
            "Outlet pressure goes negative — pipe is too long or flow too high. "
            "Try a larger diameter."
        )
    outlet_pressure = math.sqrt(outlet_sq)
    return outlet_pressure, inlet_pressure_Pa - outlet_pressure


def pipeline_capital_cost(pipe_length_m, material_cost_per_m, area_type="rural"):
    laying_cost = {"rural": 300, "urban": 700}   # EUR/m
    cost_per_m  = laying_cost.get(area_type, 300)
    return pipe_length_m * (material_cost_per_m + cost_per_m)


# Upgrading plant (Eq. 3.23, 3.24)

def upgrading_biomethane_output(biogas_flows_m3_per_h, ch4_loss_fraction,
                                 biogas_ch4_content=0.53,
                                 required_ch4_fraction=SCENARIO["min_ch4_fraction"]):
    # biogas going in × CH4 concentration ratio × (1 - loss)
    total_biogas = sum(biogas_flows_m3_per_h)
    return total_biogas * (biogas_ch4_content / required_ch4_fraction) \
           * (1 - ch4_loss_fraction)


def upgrading_electricity_use(biogas_flows_m3_per_h, energy_per_m3,
                               operating_hours=SCENARIO["operating_hours"]):
    return sum(biogas_flows_m3_per_h) * operating_hours * energy_per_m3


# Injection station (Eq. 3.25

def injection_station_opex(capacity, fixed_opex_per_unit):
    return capacity * fixed_opex_per_unit


# --- Gas storage (Eq. 3.26, 3.27) ---

def storage_electricity_use(storage_volume_m3, energy_per_m3):
    return storage_volume_m3 * energy_per_m3


# --- Line-pack (Eq. 3.30) ---

def linepack_capacity(pipe_length_m, pipe_diameter_m, max_pressure_Pa):
    pipe_volume = pipe_length_m * 0.25 * math.pi * pipe_diameter_m ** 2
    return pipe_volume * (0.6 * max_pressure_Pa)   # usable storage in the pipe itself


# =============================================================================
# 4. PERFORMANCE INDICATORS  (Eq. 3.31 – 3.41)
# =============================================================================

def compute_performance_indicators(design):

    params = SCENARIO

    # --- Biomass feedstock cost (no capital investment needed here) ---
    biomass_opex = sum(
        biomass_annual_cost(loc["b_b"])
        for loc in design.get("biomass_locations", [])
    )

    # --- Transport ---
    transport_results = []
    for route in design.get("transport_routes", []):
        fuel_energy  = transport_fuel_energy(route["l_bt"], route["b_b_t"])
        co2_emission = transport_co2_emission(fuel_energy)
        annual_cost  = transport_annual_cost(fuel_energy, route["b_b_t"], route["l_bt"])
        transport_results.append({"energy": fuel_energy, "co2": co2_emission,
                                   "opex": annual_cost, "capex": 0})

    # --- Digesters ---
    digester_results = []
    for d in design.get("digesters", []):
        elec_use  = digester_electricity_use(d["V_b_list"], d["e_d"])
        co2       = electricity_co2_emission(elec_use)
        opex      = digester_annual_opex(d["Y"], d["o_d"], elec_use)
        capex     = element_capital_cost(d["Y"], d["a_d"])
        biogas_out = digester_biogas_output(d["V_b_list"], d["c_d"])
        digester_results.append({"energy": elec_use, "co2": co2,
                                  "opex": opex, "capex": capex,
                                  "biogas_out": biogas_out})

    # --- Pre-treatments ---
    pretreat_results = []
    for p in design.get("pretreatments", []):
        elec_use = pretreat_electricity_use(p["V_d"], p["e_pt"])
        co2      = electricity_co2_emission(elec_use)
        opex     = pretreat_annual_opex(p["Y"], p["o_pt"], p["V_d"], elec_use)
        capex    = element_capital_cost(p["Y"], p["a_pt"])
        pretreat_results.append({"energy": elec_use, "co2": co2,
                                  "opex": opex, "capex": capex})

    # --- Compressors ---
    compressor_results = []
    for c in design.get("compressors", []):
        elec_use = compressor_annual_energy(c["v_c"], c["P1"], c["P2"])
        co2      = electricity_co2_emission(elec_use)
        opex     = digester_annual_opex(c["Y"], c["o_c"], elec_use)
        capex    = element_capital_cost(c["Y"], c["a_c"])
        compressor_results.append({"energy": elec_use, "co2": co2,
                                    "opex": opex, "capex": capex})

    # --- Pipelines (capital cost only — no ongoing energy or opex) ---
    pipeline_results = []
    for pl in design.get("pipelines", []):
        capex = pipeline_capital_cost(pl["l_pl"], pl["a_pl"],
                                       pl.get("area_type", "rural"))
        pipeline_results.append({"energy": 0, "co2": 0, "opex": 0, "capex": capex})

    # --- Upgrading plants ---
    upgrading_results = []
    total_biomethane_m3_per_h = 0.0
    for u in design.get("upgrading_plants", []):
        biomethane_out = upgrading_biomethane_output(u["V_d_list"], u["c_u"])
        elec_use       = upgrading_electricity_use(u["V_d_list"], u["e_u"])
        co2            = electricity_co2_emission(elec_use)
        opex           = digester_annual_opex(u["Y"], u["o_u"], elec_use)
        capex          = element_capital_cost(u["Y"], u["a_u"])
        total_biomethane_m3_per_h += biomethane_out
        upgrading_results.append({"energy": elec_use, "co2": co2,
                                   "opex": opex, "capex": capex})

    # --- Injection stations ---
    injection_results = []
    for inj in design.get("injection_stations", []):
        opex  = injection_station_opex(inj["Y"], inj["o_is"])
        capex = element_capital_cost(inj["Y"], inj["a_is"])
        injection_results.append({"energy": 0, "co2": 0, "opex": opex, "capex": capex})

    # --- Gas storages ---
    storage_results = []
    for s in design.get("gas_storages", []):
        elec_use = storage_electricity_use(s["v_st"], s["e_st"])
        co2      = electricity_co2_emission(elec_use)
        opex     = digester_annual_opex(s["Y"], s["o_st"], elec_use)
        capex    = element_capital_cost(s["Y"], s["a_st"])
        storage_results.append({"energy": elec_use, "co2": co2,
                                  "opex": opex, "capex": capex})

    # -------------------------------------------------------------------------
    # Aggregate totals across the whole supply chain
    # -------------------------------------------------------------------------
    all_elements = (transport_results + digester_results + pretreat_results
                    + compressor_results + pipeline_results + upgrading_results
                    + injection_results + storage_results)

    total_capex   = sum(e["capex"]  for e in all_elements)          # Eq. 3.31
    total_opex    = biomass_opex + sum(e["opex"] for e in all_elements)  # Eq. 3.32
    total_energy  = sum(e["energy"] for e in all_elements)           # Eq. 3.36
    total_co2_t   = sum(e["co2"]    for e in all_elements) / 1000   # Eq. 3.39, kg → tonnes

    # Eq. 3.33 — annual biomethane production
    annual_biomethane_m3 = total_biomethane_m3_per_h * params["operating_hours"]

    # Eq. 3.34 — annual revenue (gas price + subsidy)
    annual_revenue = annual_biomethane_m3 * (params["gas_price"] + params["biomethane_subsidy"])

    # -------------------------------------------------------------------------
    # Five performance indicators
    # -------------------------------------------------------------------------

    # Eq. 3.35 — NPV
    npv = -total_capex + present_worth(annual_revenue - total_opex)

    # Eq. 3.37 — net energy production (energy content of biomethane minus energy consumed)
    net_energy_kwh = annual_biomethane_m3 * params["heating_value_natural_gas"] - total_energy

    # Eq. 3.38 — biomethane cost (annualised capex + opex spread over production volume)
    biomethane_cost = (annual_worth(total_capex) + total_opex) / annual_biomethane_m3 \
                      if annual_biomethane_m3 > 0 else float("inf")

    # Eq. 3.40 — CO2 emission reduction vs. equivalent natural gas use
    co2_reduction_t = annual_biomethane_m3 * params["co2_emission_natural_gas"] / 1000 \
                      - total_co2_t

    # Eq. 3.41 — cost per tonne of CO2 avoided
    co2_cost = (annual_worth(total_capex) + total_opex) / co2_reduction_t \
               if co2_reduction_t > 0 else float("inf")

    return {
        "npv":              round(npv, 2),
        "net_energy":       round(net_energy_kwh, 2),
        "biomethane_cost":  round(biomethane_cost, 6),
        "co2_reduction":    round(co2_reduction_t, 2),
        "co2_cost":         round(co2_cost, 6),
        # intermediates — handy for debugging
        "_total_capex":          round(total_capex, 2),
        "_total_opex":           round(total_opex, 2),
        "_annual_biomethane_m3": round(annual_biomethane_m3, 2),
        "_total_energy":         round(total_energy, 2),
        "_total_co2_tonnes":     round(total_co2_t, 2),
    }



def ask(prompt, default):
    """Ask the user a question. If they just press Enter, use the default value."""
    response = input(f"  {prompt} [default: {default}]: ").strip()
    if response == "":
        return default
    return type(default)(response)   # convert to same type as default (int or float)


def ask_int(prompt, default):
    response = input(f"  {prompt} [default: {default}]: ").strip()
    return int(response) if response != "" else default


def collect_inputs():
    """Walk the user through entering all supply chain parameters."""

    print("\n" + "=" * 60)
    print("  BIOMETHANE SUPPLY CHAIN — INPUT WIZARD")
    print("  Press Enter to keep the default value shown in [ ]")
    print("=" * 60)

    design = {
        "biomass_locations": [],
        "transport_routes":  [],
        "digesters":         [],
        "pretreatments":     [],
        "compressors":       [],
        "pipelines":         [],
        "upgrading_plants":  [],
        "injection_stations":[],
        "gas_storages":      [],
    }

   
    print("\n--- BIOMASS LOCATIONS ---")
    n_biomass = ask_int("How many biomass locations do you have?", 2)

    for i in range(n_biomass):
        print(f"\n  Location {i + 1}:")
        flow = ask("Biomass flow (kg/h)", 1000.0)
        design["biomass_locations"].append({"b_b": flow})

 
    print("\n--- TRANSPORT ---")
    n_routes = ask_int("How many truck transport routes? (0 if biomass is on-site)", 0)

    for i in range(n_routes):
        print(f"\n  Route {i + 1}:")
        dist  = ask("Distance (km)", 20.0)
        flow  = ask("Biomass flow on this route (kg/h)", 500.0)
        fuel  = transport_fuel_energy(dist, flow)
        design["transport_routes"].append({"l_bt": dist, "b_b_t": flow})
   
    print("\n--- DIGESTERS ---")
    n_digesters = ask_int("How many digesters?", 2)

    digester_biogas_outputs = []   # needed later for upgrading plant input

    for i in range(n_digesters):
        print(f"\n  Digester {i + 1}:")
        flow      = ask("Biomass flow into this digester (kg/h)", 1000.0)
        heat_loss = ask("Heat loss fraction (biogas burned for heating)", 0.06)
        elec      = ask("Electricity use (kWh per m3 of biogas)", 0.30)
        opex      = ask("Fixed annual opex (EUR/year)", 35000.0)
        capex     = ask("Capital cost (EUR)", 700000.0)

        biogas_vol = biomass_to_biogas_volume(flow)
        biogas_out = digester_biogas_output([biogas_vol], heat_loss)
        digester_biogas_outputs.append(biogas_out)

        design["digesters"].append({
            "V_b_list": [biogas_vol],
            "c_d": heat_loss,
            "e_d": elec,
            "Y":   1,
            "o_d": opex,
            "a_d": capex,
        })


    print("\n--- PRE-TREATMENT ---")
    n_pt = ask_int("How many pre-treatment units? (0 if not needed)", 0)

    for i in range(n_pt):
        print(f"\n  Pre-treatment {i + 1}:")
        biogas_flow = ask("Biogas flow being cleaned (m3/h)", 282.0)
        elec        = ask("Electricity use (kWh per m3)", 0.10)
        opex        = ask("Fixed annual opex (EUR/year)", 10000.0)
        capex       = ask("Capital cost (EUR)", 200000.0)
        design["pretreatments"].append({
            "V_d":  biogas_flow,
            "e_pt": elec,
            "Y":    1,
            "o_pt": opex,
            "a_pt": capex,
        })


    print("\n--- COMPRESSORS ---")
    n_comp = ask_int("How many compressors? (0 if not needed)", 0)

    for i in range(n_comp):
        print(f"\n  Compressor {i + 1}:")
        flow  = ask("Gas flow (m3/h)", 282.0)
        p_in  = ask("Inlet pressure (bar)", 1.0)
        p_out = ask("Outlet pressure (bar)", 8.0)
        opex  = ask("Fixed annual opex (EUR/year)", 8000.0)
        capex = ask("Capital cost (EUR)", 150000.0)
        design["compressors"].append({
            "v_c": flow,
            "P1":  p_in,
            "P2":  p_out,
            "Y":   1,
            "o_c": opex,
            "a_c": capex,
        })

    print("\n--- PIPELINES ---")
    n_pipes = ask_int("How many pipeline segments?", 1)

    for i in range(n_pipes):
        print(f"\n  Pipeline {i + 1}:")
        length   = ask("Length (metres)", 500.0)
        mat_cost = ask("Material cost (EUR per metre)", 15.0)
        area     = input("  Area type — rural or urban? [default: rural]: ").strip()
        if area not in ("rural", "urban"):
            area = "rural"
        design["pipelines"].append({
            "l_pl":      length,
            "a_pl":      mat_cost,
            "area_type": area,
        })

   
    print("\n--- UPGRADING PLANTS ---")
    n_up = ask_int("How many upgrading plants?", 1)

    for i in range(n_up):
        print(f"\n  Upgrading plant {i + 1}:")
        print(f"  (Digester biogas outputs calculated so far: "
              f"{[round(x, 1) for x in digester_biogas_outputs]} m3/h)")
        use_all = input("  Use all digester outputs as input to this plant? (y/n) [default: y]: ").strip()
        if use_all.lower() == "n":
            flows_input = input("  Enter biogas flows separated by commas (e.g. 282, 282): ")
            biogas_flows = [float(x.strip()) for x in flows_input.split(",")]
        else:
            biogas_flows = digester_biogas_outputs

        ch4_loss = ask("CH4 loss fraction during upgrading", 0.015)
        elec     = ask("Electricity use (kWh per m3 of biogas)", 0.30)
        opex     = ask("Fixed annual opex (EUR/year)", 45000.0)
        capex    = ask("Capital cost (EUR)", 1200000.0)
        design["upgrading_plants"].append({
            "V_d_list": biogas_flows,
            "c_u":  ch4_loss,
            "e_u":  elec,
            "Y":    1,
            "o_u":  opex,
            "a_u":  capex,
        })

    print("\n--- INJECTION STATIONS ---")
    n_inj = ask_int("How many injection stations?", 1)

    for i in range(n_inj):
        print(f"\n  Injection station {i + 1}:")
        opex  = ask("Fixed annual opex (EUR/year)", 3500.0)
        capex = ask("Capital cost (EUR)", 55000.0)
        design["injection_stations"].append({
            "Y":    1,
            "o_is": opex,
            "a_is": capex,
        })

  
    print("\n--- GAS STORAGE ---")
    n_stor = ask_int("How many gas storage units? (0 if not needed)", 0)

    for i in range(n_stor):
        print(f"\n  Storage {i + 1}:")
        volume = ask("Storage volume (m3)", 500.0)
        elec   = ask("Electricity use (kWh per m3)", 0.05)
        opex   = ask("Fixed annual opex (EUR/year)", 5000.0)
        capex  = ask("Capital cost (EUR)", 100000.0)
        design["gas_storages"].append({
            "v_st": volume,
            "e_st": elec,
            "Y":    1,
            "o_st": opex,
            "a_st": capex,
        })

    return design


if __name__ == "__main__":

    design  = collect_inputs()
    results = compute_performance_indicators(design)

    print("\n" + "=" * 60)
    print("  BIOMETHANE SUPPLY CHAIN — PERFORMANCE INDICATORS")
    print("=" * 60)
    print(f"  Total Capital Cost      :  EUR {results['_total_capex']:>15,.2f}")
    print(f"  Total Operational Cost  :  EUR {results['_total_opex']:>15,.2f} /a")
    print(f"  Biomethane Production   :  {results['_annual_biomethane_m3']:>15,.0f} m3(n)/a")
    print("-" * 60)
    print(f"  NPV                     :  EUR {results['npv']:>15,.2f}")
    print(f"  Net Energy Production   :  {results['net_energy']:>15,.0f} kWh/a")
    print(f"  Biomethane Cost         :  EUR {results['biomethane_cost']:.4f} /m3(n)")
    print(f"  CO2 Emission Reduction  :  {results['co2_reduction']:>15,.2f} t/a")
    print(f"  CO2 Cost                :  EUR {results['co2_cost']:.4f} /kg CO2")
    print("=" * 60)
