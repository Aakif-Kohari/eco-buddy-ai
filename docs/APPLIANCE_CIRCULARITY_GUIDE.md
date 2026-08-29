# 🔌 Smart Appliance Circularity & Lifecycle Engine

## 📖 Overview

The **Smart Appliance Circularity & Lifecycle Engine** gives consumers and enterprise asset managers data-driven guidance on repair vs replace decisions, powered by Weibull reliability hazard functions and embodied carbon lifecycle assessment ($\text{LCA}$).

---

## 🔬 Scientific & Economic Methodologies

1. **Weibull Conditional Failure Risk**:
   Computes the probability of breakdown across the subsequent 2-year window:
   $$P(t \le T \le t+2 \mid T > t) = 1 - \exp\left(-\left(\frac{t+2}{\eta}\right)^\beta + \left(\frac{t}{\eta}\right)^\beta\right)$$
2. **Avoided Manufacturing Embodied Carbon**:
   Quantifies $\text{kg CO}_2\text{e}$ preserved by extending operational lifespan rather than triggering virgin raw material extraction and production.
3. **50% Economic Payback Benchmark**:
   Compares annualized capital costs of repair against replacement depreciation.

---

## 🧪 Testing

Run test suite:
```bash
python -m pytest tests/test_appliance_circularity_engine.py -v
```
