/**
 * Enterprise Architectural Specification & Header:
 * Module: Smart Water Management & RO Desalination Core Service Engine
 * File: src/services/smart_water_engine.js
 * Standard: ECMAScript 2022 Class Specification, ISO 14046 Water Footprint Standard
 * Scope: High-Throughput Hydrological Telemetry, Desalination Specific Energy Consumption (SEC),
 *        Membrane Fouling Rate Prediction (SDI/ΔP), and Multi-Stage Water Recycling Balance.
 *
 * Technical Specifications:
 * - Osmotic Pressure (Π) Calculation: Van 't Hoff Equation (Π = i * M * R * T)
 * - Specific Energy Consumption: SEC = (P_feed * Q_feed - P_brine * Q_brine * η_erd) / (36 * Q_permeate * η_pump)
 * - Membrane Permeate Water Flux: J_w = A * (ΔP - ΔΠ)
 * - Salt Pass & Rejection Analytics: R_s = (1 - C_p / C_f) * 100%
 */

class SmartWaterEngine {
  /**
   * Initialize Smart Water Engine with default thermodynamic constants & telemetry configs
   * @param {Object} config - Engine initialization configuration object
   */
  constructor(config = {}) {
    this.gasConstantR = 0.08206; // L·atm/(mol·K)
    this.temperatureKelvin = config.defaultTempK || 298.15; // 25°C default
    this.osmoticCoeff = config.osmoticCoeff || 0.92; // Seawater osmotic activity coefficient
    
    // Facility Default State Telemetry Model
    this.facilityState = {
      facilityId: config.facilityId || 'FAC-RO-01',
      rawIntakeFlow: config.rawIntakeFlow || 300000, // m³/day
      feedSalinityTDS: config.feedSalinityTDS || 35400, // mg/L or ppm
      recoveryTarget: config.recoveryTarget || 0.485, // 48.5% recovery
      erdEfficiency: config.erdEfficiency || 0.972, // Isobaric ERD Efficiency (97.2%)
      pumpEfficiency: config.pumpEfficiency || 0.88, // High-Pressure Pump Efficiency (88%)
      membraneArea: config.membraneArea || 450000, // Total Membrane Surface Area (m²)
      permeabilityA: config.permeabilityA || 1.15, // Water Permeability Coeff A (L/m²·h·bar)
      recycledBlendRatio: config.recycledBlendRatio || 0.15 // 15% wastewater blend rate
    };

    // Sensor Telemetry Cache
    this.telemetryCache = new Map();
    this.initDefaultTelemetry();
  }

  /**
   * Initializes default mock telemetry streams for connected RO Trains and Sensor Nodes
   */
  initDefaultTelemetry() {
    this.telemetryCache.set('TRAIN-ALPHA', {
      id: 'TRAIN-ALPHA',
      type: 'SWRO',
      feedPressureBar: 64.5,
      diffPressureBar: 1.82,
      saltRejectionPct: 99.74,
      sdiIndex: 2.1,
      membraneAgeMonths: 18,
      status: 'OPERATIONAL'
    });

    this.telemetryCache.set('TRAIN-BRAVO', {
      id: 'TRAIN-BRAVO',
      type: 'BWRO',
      feedPressureBar: 18.2,
      diffPressureBar: 1.15,
      saltRejectionPct: 99.88,
      sdiIndex: 1.4,
      membraneAgeMonths: 9,
      status: 'OPERATIONAL'
    });
  }

  /**
   * Calculates Thermodynamic Osmotic Pressure (Π) in Bar based on TDS concentration
   * Formula: Π (bar) = (TDS_gL / MW_NaCl) * i * R * T * OsmoticCoeff * 1.01325
   * @param {number} tdsPpm - Total Dissolved Solids in mg/L (ppm)
   * @param {number} tempCelsius - Water Temperature in °C
   * @returns {number} Osmotic Pressure in Bar
   */
  calculateOsmoticPressure(tdsPpm, tempCelsius = 25) {
    if (typeof tdsPpm !== 'number' || tdsPpm < 0) {
      throw new Error('Invalid TDS concentration: Must be a non-negative number.');
    }
    const tempK = tempCelsius + 273.15;
    const molarityNaCl = (tdsPpm / 1000) / 58.44; // mol/L assuming NaCl equivalent
    const ionFactor = 2.0; // Na+ and Cl-
    const pressureAtm = ionFactor * molarityNaCl * this.gasConstantR * tempK * this.osmoticCoeff;
    const pressureBar = pressureAtm * 1.01325; // Convert atm to bar
    return parseFloat(pressureBar.toFixed(2));
  }

  /**
   * Calculates Reverse Osmosis Specific Energy Consumption (SEC) in kWh/m³
   * Formula: SEC = [P_feed - (P_brine * η_erd * (1 - Recovery))] / (36 * Recovery * η_pump)
   * @param {number} feedPressureBar - High Pressure Pump Feed Pressure (bar)
   * @param {number} recoveryRate - Recovery Fraction (0.30 - 0.85)
   * @param {number} erdEfficiency - Energy Recovery Device Efficiency Fraction (0.80 - 0.99)
   * @param {number} pumpEfficiency - High Pressure Pump Efficiency Fraction (0.75 - 0.95)
   * @returns {number} SEC in kWh/m³
   */
  calculateSpecificEnergyConsumption(
    feedPressureBar = 64.5,
    recoveryRate = 0.485,
    erdEfficiency = 0.972,
    pumpEfficiency = 0.88
  ) {
    if (recoveryRate <= 0 || recoveryRate >= 1.0) {
      throw new Error('Recovery rate must be a fraction strictly between 0 and 1.');
    }

    const brinePressureBar = feedPressureBar * 0.96; // 4% pressure drop across vessel
    const netPressureReq = feedPressureBar - (brinePressureBar * erdEfficiency * (1.0 - recoveryRate));
    const secKwhPerM3 = netPressureReq / (36.0 * recoveryRate * pumpEfficiency);

    return parseFloat(secKwhPerM3.toFixed(2));
  }

  /**
   * Predicts Membrane Fouling Trend & Cleaning In Place (CIP) Urgency Score (0 - 100)
   * Based on Silt Density Index (SDI), Differential Pressure (ΔP), and Operational Hours
   * @param {number} sdiIndex - Silt Density Index 15-min rating
   * @param {number} diffPressureBar - Differential Pressure across vessel stage
   * @param {number} operatingHours - Hours elapsed since last CIP cycle
   * @returns {Object} Fouling risk assessment metrics
   */
  predictMembraneFouling(sdiIndex, diffPressureBar, operatingHours) {
    const sdiPenalty = Math.max(0, (sdiIndex - 3.0) * 15);
    const dpPenalty = Math.max(0, (diffPressureBar - 1.5) * 40);
    const timePenalty = (operatingHours / 4380) * 20; // 4380 hrs = 6 months target

    const totalRiskScore = Math.min(100, parseFloat((sdiPenalty + dpPenalty + timePenalty).toFixed(1)));
    
    let cipUrgency = 'LOW';
    if (totalRiskScore >= 75) {
      cipUrgency = 'CRITICAL';
    } else if (totalRiskScore >= 45) {
      cipUrgency = 'MEDIUM';
    }

    return {
      riskScore: totalRiskScore,
      cipUrgency: cipUrgency,
      recommendedAction: cipUrgency === 'CRITICAL' ? 'Schedule Acid/Alkaline CIP Clean Immediately' : 'Continue Normal Anti-scalant Injection'
    };
  }

  /**
   * Simulates Closed-Loop Water Mass Balance & CO2 Carbon Offset Potential
   * @param {Object} inputParams - Simulation Parameters Override
   * @returns {Object} Complete Mass Balance & Decarbonization Assessment
   */
  simulateMassBalance(inputParams = {}) {
    const intake = inputParams.rawIntakeFlow || this.facilityState.rawIntakeFlow;
    const recovery = (inputParams.targetRecoveryPct !== undefined ? inputParams.targetRecoveryPct / 100 : this.facilityState.recoveryTarget);
    const erdEff = (inputParams.erdEfficiencyPct !== undefined ? inputParams.erdEfficiencyPct / 100 : this.facilityState.erdEfficiency);
    const blendRate = (inputParams.recycledBlendRatioPct !== undefined ? inputParams.recycledBlendRatioPct / 100 : this.facilityState.recycledBlendRatio);

    const permeateFlow = intake * recovery * (1 + blendRate * 0.5);
    const brineDischargeFlow = intake - permeateFlow;
    const feedPressure = 62.0 + (recovery * 10.0);

    const sec = this.calculateSpecificEnergyConsumption(feedPressure, recovery, erdEff, this.facilityState.pumpEfficiency);
    
    // Baseline Grid Emission Factor: 0.475 kg CO2e / kWh
    // Carbon Offset derived from wastewater blend recycling vs raw ocean pumping
    const energySavedPerM3 = 0.45 * blendRate; // kWh saved per m³ recycled
    const dailyEnergySavedKwh = permeateFlow * energySavedPerM3;
    const dailyCo2OffsetTonnes = parseFloat(((dailyEnergySavedKwh * 0.475) / 1000).toFixed(2));

    return {
      netPermeateFlowM3: Math.round(permeateFlow),
      brineDischargeFlowM3: Math.round(brineDischargeFlow),
      specificEnergyConsumptionKwhM3: sec,
      dailyCo2OffsetTonnes: dailyCo2OffsetTonnes,
      sustainabilityGrade: dailyCo2OffsetTonnes > 10 ? 'A+' : 'A'
    };
  }

  /**
   * Sanitizes user input string against HTML script injection vulnerabilities
   * @param {string} str - Raw user input string
   * @returns {string} Sanitized clean string
   */
  sanitizeInput(str) {
    if (typeof str !== 'string') return '';
    return str.replace(/[&<>"']/g, (match) => {
      const entityMap = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
      };
      return entityMap[match];
    });
  }
}

// Browser & Node Environment Module Export Compatibility
if (typeof module !== 'undefined' && module.exports) {
  module.exports = SmartWaterEngine;
} else if (typeof window !== 'undefined') {
  window.SmartWaterEngine = SmartWaterEngine;
  
  // UI Event Handler Integration Initialization
  document.addEventListener('DOMContentLoaded', () => {
    const engine = new SmartWaterEngine();
    
    const runSimBtn = document.getElementById('btn-run-simulation');
    if (runSimBtn) {
      runSimBtn.addEventListener('click', () => {
        const rawIntake = parseFloat(document.getElementById('input-raw-intake').value);
        const targetRec = parseFloat(document.getElementById('input-target-recovery').value);
        const erdEff = parseFloat(document.getElementById('input-erd-efficiency').value);
        const blend = parseFloat(document.getElementById('input-recycled-blend').value);

        const results = engine.simulateMassBalance({
          rawIntakeFlow: rawIntake,
          targetRecoveryPct: targetRec,
          erdEfficiencyPct: erdEff,
          recycledBlendRatioPct: blend
        });

        document.getElementById('res-net-permeate').textContent = `${results.netPermeateFlowM3.toLocaleString()} m³/d`;
        document.getElementById('res-brine-flow').textContent = `${results.brineDischargeFlowM3.toLocaleString()} m³/d`;
        document.getElementById('res-power-req').textContent = `${results.specificEnergyConsumptionKwhM3} kWh/m³`;
        document.getElementById('res-co2-offset').textContent = `-${results.dailyCo2OffsetTonnes} tCO2e/day`;
      });
    }

    const refreshBtn = document.getElementById('btn-trigger-refresh');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => {
        const throughputEl = document.getElementById('kpi-val-throughput');
        if (throughputEl) {
          const newVal = (140 + Math.random() * 5).toFixed(1);
          throughputEl.textContent = newVal;
        }
      });
    }
  });
}
