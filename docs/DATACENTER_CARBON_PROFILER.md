# 🚀 Green Software & Data Center AI Carbon Profiler

## 📖 Overview

The **Green Software & Data Center AI Carbon Profiler** provides enterprise-grade accounting and optimization for computational workloads, artificial intelligence training, and hyper-scale infrastructure.

As modern machine learning and computational workloads surge, calculating accurate environmental impact requires moving beyond simplistic flat power estimations to multidimensional physics and grid-aware models.

---

## 🔬 Core Methodologies

### 1. Scope 2: Grid-Aware Operational Emissions
Calculates hourly and regional operational emissions based on real-world marginal grid carbon intensities ($g\text{CO}_2\text{e/kWh}$) across key cloud regions (`us-east-1`, `us-west-2`, `eu-west-1`, `eu-north-1`, `ap-south-1`).

$$\text{Energy}_{\text{facility}} = \text{Energy}_{\text{compute}} \times \text{PUE}_{\text{effective}}$$

$$\text{Emissions}_{\text{operational}} = \text{Energy}_{\text{facility}} \times \text{CarbonIntensity}_{\text{grid}}$$

### 2. Scope 3: Hardware Lifecycle Embodied Carbon
Amortizes cradle-to-gate chip fabrication emissions (silicon die extraction, lithography, packaging, PCB assembly) across the hardware's operational lifespan:

$$\text{Emissions}_{\text{embodied}} = N_{\text{chips}} \times \text{EmbodiedCarbon}_{\text{unit}} \times \left(\frac{\text{JobDuration}_{\text{hours}}}{\text{Lifespan}_{\text{hours}}}\right)$$

### 3. Thermodynamic Cooling Overhead (PUE & WUE)
Models power usage effectiveness (PUE) and water usage effectiveness (WUE in L/kWh) across diverse cooling technologies:
- **Direct-to-Chip Liquid Cooling**: PUE delta -0.05, WUE 0.15 L/kWh
- **Rear-Door Heat Exchangers**: PUE delta 0.00, WUE 0.35 L/kWh
- **Conventional CRAC Air Cooling**: PUE delta +0.15, WUE 1.20 L/kWh
- **Two-Phase Immersion Cooling**: PUE delta -0.09, WUE 0.02 L/kWh

### 4. Spatial & Temporal Carbon Optimization
Identifies alternative cloud regions with lower instantaneous grid intensity and quantifies:
- Percentage carbon emissions reduction ($\%$)
- Avoided emissions in $\text{kg CO}_2\text{e}$
- Water savings in Liters
- Net cost differential ($\Delta \text{USD}$)

---

## 🧪 Testing

Run the profiler test suite:
```bash
python -m pytest tests/test_datacenter_carbon_engine.py -v
```
