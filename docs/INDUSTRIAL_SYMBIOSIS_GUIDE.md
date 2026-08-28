# 🏭 Industrial Symbiosis & Waste Heat Recovery Engine

## 📖 Overview

The **Industrial Symbiosis & Waste Heat Recovery Engine** enables manufacturing plants, thermal utilities, data centers, and eco-industrial parks to model heat exchanger network potentials and thermodynamic energy cascades.

---

## 🔬 Physics & Thermodynamic Models

1. **Enthalpy Transfer Rate**:
   $$\dot{Q} = \dot{m} \cdot c_p \cdot (T_{\text{inlet}} - T_{\text{target}})$$
2. **Technological Recovery Efficiencies**:
   - Plate & Frame District Heating Exchanger: $88\%$
   - Organic Rankine Cycle (ORC) Power: $18\%$
   - Absorption Chiller COP: $72\%$
   - Heat Pipe Economizer: $78\%$
3. **Avoided Emissions**:
   Converts recovered MWh thermal into displaced baseline fuel combustion emissions (Scope 1 natural gas / coal displacement).

---

## 🧪 Testing

Run test suite:
```bash
python -m pytest tests/test_industrial_symbiosis_engine.py -v
```
