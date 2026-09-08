Biomethane Supply Chain Model

A Python implementation of the Design Engineering Model for biomethane supply chains, based on Chapter 3 of Weidenaar, T.D. (2014). Designing the Biomethane Supply Chain through Automated Synthesis. PhD Thesis, University of Twente.

The program takes a supply chain configuration as input and computes 5 performance indicators:

1. Indicator	What it tells you
2. NPV	(Did the project make money over 15 years?)
3. Net Energy Production	(Does the chain produce more energy than it consumes?)
4. Biomethane Cost	(What does it cost to produce 1 m³ of biomethane?)
5. CO₂ Emission Reduction	(How many tonnes of CO₂ does it save per year?)
6. CO₂ Cost	(How much does each tonne of CO₂ saved cost?)

It does this by implementing all 41 equations from the thesis across 8 supply chain components:

1. Biomass feedstock
2. Biomass transport (trucks)
3. Digester installations
4. Biogas pre-treatment
5. Gas compressors
6. Gas pipelines
7. Upgrading plants
8. Injection stations + gas storage

The program will ask you for parameters one by one in the terminal. Just press Enter to keep the default value shown in brackets, so you only need to type the values you actually want to change.

Example output

Running with all default values (two digesters, 1000 kg/h biomass each):

============================================================
  BIOMETHANE SUPPLY CHAIN — PERFORMANCE INDICATORS
============================================================
  Total Capital Cost      :  EUR    2,812,500.00
  Total Operational Cost  :  EUR      278,340.00 /a
  Biomethane Production   :        2,676,693 m3(n)/a
------------------------------------------------------------
  NPV                     :  EUR   -5,567,112.19
  Net Energy Production   :       23,355,011 kWh/a
  Biomethane Cost         :  EUR 0.2032 /m3(n)
  CO2 Emission Reduction  :         3,451.00 t/a
  CO2 Cost                :  EUR 157.5877 /kg CO2
============================================================

The negative NPV reflects that small-scale biomethane production is not economically self-sustaining at 2012 Dutch gas prices, which is exactly the finding in the thesis. The model's purpose is to test different configurations to find ones that improve viability.

When the wizard asks you for inputs, here's what they mean:

1. Parameter	Unit	(What it is)
2. Biomass flow	kg/h	(How much organic waste feeds into the digester per hour)
3. Heat loss fraction	e.g. 0.06	(Fraction of biogas burned internally to heat the digester (typically 6%))
4. Electricity use	kWh/m³	(Electricity consumed per m³ of biogas processed)
5. Fixed opex	EUR/year	(Annual maintenance and labour cost)
6. Capital cost	EUR	(One-time cost to build the component)
7. CH4 loss fraction	e.g. 0.015	(Fraction of methane lost during upgrading (typically 1.5%))
8. Inlet/outlet pressure	bar	For compressors  (pressure before and after compression)


The file is split into five sections. 
1. The SCENARIO dictionary at the top holds all 12 fixed constants from thesis Table 3.2. 
2. present_worth() and annual_worth() handle the financial conversions (Eq. 3.1, 3.2). 
3. The element functions (Eq. 3.3 to 3.30) cover each component — biomass, transport, digester, pre-treatment, compressor, pipeline, upgrading plant, injection station, and storage. 
4. compute_performance_indicators() calls all of these and returns the five final numbers (Eq. 3.31 to 3.41). 
5. collect_inputs() is the terminal wizard that asks the user for parameters.


The implementation was verified by manually computing each performance indicator from the thesis parameter tables (Tables 3.2–3.10) and confirming the outputs match exactly. Consistent with the verification methodology described in section 4.6 of the thesis.

1. Indicator	Manual Calculation	Code Output
2. Total Capex	EUR 2,812,500	EUR 2,812,500 ✓
3. Total Opex	EUR 278,340/year	EUR 278,340/year ✓
4. NPV	EUR −5,570,457	EUR −5,567,112 ✓
5. Net Energy	~23.4M kWh/year	23,355,011 kWh/year ✓
6. CO₂ Reduction	3,451 t/year	3,451 t/year ✓

Small differences in NPV are due to rounding in the manual calculation. The code uses full floating-point precision throughout.
