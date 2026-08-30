# ❄️ Bioclimatic Passive Cooling & Thermal Comfort Engine

## 📖 Overview

The **Bioclimatic Passive Cooling & Thermal Comfort Engine** models building physics, diurnal thermal mass damping, natural stack-effect night ventilation, and Fanger PMV/PPD thermal comfort standards (ASHRAE 55 / ISO 7730).

---

## 🔬 Core Physical Principles

1. **Diurnal Temperature Damping & Phase Lag**:
   $$T_{\text{indoor, peak}} = T_{\text{outdoor, mean}} + \left(\frac{\Delta T_{\text{diurnal}}}{2}\right) \cdot \mu_{\text{decrement}} + \text{SolarGain}$$
2. **Stack-Effect Natural Airflow Rate**:
   $$\dot{V} = C_d \cdot A_{\text{opening}} \cdot \sqrt{\frac{2 \cdot g \cdot h \cdot \Delta T}{T_{\text{mean}}}}$$
3. **Fanger PMV / PPD Indices**:
   Evaluates predicted mean vote ($\text{PMV}$) and predicted percentage dissatisfied ($\text{PPD}$).

---

## 🧪 Testing

Run test suite:
```bash
python -m pytest tests/test_passive_comfort_engine.py -v
```
