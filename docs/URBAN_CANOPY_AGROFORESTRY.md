# 🌳 Urban Heat Island & Agroforestry Canopy Planner

## 📖 Overview

The **Urban Heat Island & Agroforestry Canopy Planner** introduces microclimate simulation, species-specific thermodynamic evapotranspiration, and rainwater bio-retention modeling into EcoBuddy AI.

---

## 🔬 Core Modeling Capabilities

1. **Evapotranspiration & Latent Heat Absorption**: Converts tree transpiration volume into equivalent latent cooling energy ($\text{kWh/yr}$) using water vaporization thermodynamics ($2.26\text{ MJ/kg}$).
2. **Surface vs Ambient Microclimate Cooling**: Simulates surface temperature mitigation based on impervious surface fractions and leaf area index ($\text{LAI}$).
3. **Stormwater Bio-retention**: Quantifies runoff volume absorbed by soil substrate permutations (bioswale matrix, loamy, compacted clay).
4. **Agroforestry Carbon Sequestration**: Computes tree biomass carbon capture rates.

---

## 🧪 Testing

Run test suite:
```bash
python -m pytest tests/test_urban_canopy_engine.py -v
```
