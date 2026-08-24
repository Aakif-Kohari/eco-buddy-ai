/**
 * Enterprise Architectural Specification & Header:
 * Module: Sustainable Aviation Fuel (SAF) Production & Lifecycle Analytics Engine
 * File: src/services/saf_lifecycle_engine.js
 * Standard: ECMAScript 2022 Class Specification, ICAO CORSIA SAF Lifecycle Methodology
 * Scope: Hydroprocessed Esters and Fatty Acids (HEFA), Power-to-Liquid (PtL), Alcohol-to-Jet (AtJ),
 *        Well-to-Wake (WtW) Carbon Intensity (CI) Accounting, ASTM D7566 Synthetic Kerosene Blend Certification.
 *
 * Technical Specifications:
 * - Conventional Jet-A1 Baseline CI: 89.0 gCO2e / MJ (ICAO CORSIA default)
 * - SAF Carbon Intensity: CI_total = CI_feedstock_farming + CI_processing + CI_transport - CI_ccus_credit
 * - Percentage GHG Reduction: GHG_reduction = ((89.0 - CI_SAF) / 89.0) * 100%
 * - Aviation Abatement: Abatement_tCO2e = Volume_tonnes * 43.8 MJ/kg * (89.0 - CI_SAF) / 1,000,000
 */

class SafLifecycleEngine {
  /**
   * Initialize SAF Engine with default CORSIA lifecycle constants & plant configs
   * @param {Object} config - Engine initialization configuration object
   */
  constructor(config = {}) {
    this.jetA1BaselineCi = 89.0; // gCO2e / MJ
    this.jetEnergyDensityMjKg = 43.8; // MJ / kg
    
    // Plant Default State Telemetry Model
    this.plantState = {
      plantId: config.plantId || 'SAF-HEFA-01',
      pathway: config.pathway || 'HEFA-UCO', // HEFA-UCO, PtL, AtJ, FT
      annualProductionTonnes: config.annualProductionTonnes || 500000,
      hydrogenSource: config.hydrogenSource || 'GREEN', // GREEN, BLUE, GREY
      blendLimitPct: config.blendLimitPct || 50.0, // ASTM D7566 max limit
      freezePointCelsius: config.freezePointCelsius || -48.5,
      densityKgM3: config.densityKgM3 || 758.2
    };

    // Feedstock Default CI Database (gCO2e / MJ)
    this.feedstockCiDatabase = {
      'UCO': { farming: 0.0, transport: 5.2, refining: 13.2 },
      'TALLOW': { farming: 0.0, transport: 6.8, refining: 18.5 },
      'PTL_EPOWER': { farming: 0.0, transport: 1.5, refining: 6.5 },
      'ETHANOL': { farming: 24.5, transport: 4.1, refining: 22.0 }
    };

    // Hydrogen Refining Penalty Map (gCO2e / MJ penalty)
    this.hydrogenPenaltyMap = {
      'GREEN': 0.0,
      'BLUE': 3.5,
      'GREY': 14.8
    };

    this.telemetryCache = new Map();
    this.initDefaultTelemetry();
  }

  /**
   * Initializes default mock telemetry streams for connected Refinery Reactors
   */
  initDefaultTelemetry() {
    this.telemetryCache.set('STAGE-01-HDO', {
      id: 'STAGE-01-HDO',
      name: 'Hydrodeoxygenation',
      pressureBar: 85.4,
      temperatureC: 365.2,
      h2ConsumptionWtPct: 3.8,
      status: 'OPERATIONAL'
    });

    this.telemetryCache.set('STAGE-02-ISOMER', {
      id: 'STAGE-02-ISOMER',
      name: 'Hydroisomerization',
      pressureBar: 62.0,
      temperatureC: 340.8,
      freezePointC: -48.5,
      status: 'OPERATIONAL'
    });
  }

  /**
   * Calculates Well-to-Wake (WtW) Carbon Intensity (CI) in gCO2e/MJ
   * @param {string} feedstockKey - Feedstock key ('UCO', 'TALLOW', 'PTL_EPOWER', 'ETHANOL')
   * @param {string} h2SourceKey - Hydrogen source ('GREEN', 'BLUE', 'GREY')
   * @returns {number} Carbon Intensity in gCO2e / MJ
   */
  calculateCarbonIntensity(feedstockKey = 'UCO', h2SourceKey = 'GREEN') {
    const feedstockData = this.feedstockCiDatabase[feedstockKey] || this.feedstockCiDatabase['UCO'];
    const h2Penalty = this.hydrogenPenaltyMap[h2SourceKey] !== undefined ? this.hydrogenPenaltyMap[h2SourceKey] : 0.0;

    const netCi = feedstockData.farming + feedstockData.transport + feedstockData.refining + h2Penalty;
    return parseFloat(netCi.toFixed(1));
  }

  /**
   * Calculates Percentage GHG Reduction compared to conventional Jet-A1 baseline (89 gCO2e/MJ)
   * Formula: GHG_reduction = ((89.0 - CI_SAF) / 89.0) * 100%
   * @param {number} safCi - Calculated SAF Carbon Intensity (gCO2e/MJ)
   * @returns {number} Percentage reduction in GHG emissions (%)
   */
  calculateGhgReductionPercentage(safCi = 18.4) {
    if (safCi < 0) {
      throw new Error('Carbon Intensity cannot be negative.');
    }

    const reductionPct = ((this.jetA1BaselineCi - safCi) / this.jetA1BaselineCi) * 100.0;
    return parseFloat(reductionPct.toFixed(1));
  }

  /**
   * Simulates ICAO CORSIA Lifecycle Abatement & Annual CO2 Reduction
   * @param {Object} params - Simulation Overrides
   * @returns {Object} Comprehensive CORSIA lifecycle assessment results
   */
  simulateCorsiaLifecycle(params = {}) {
    const feedstock = params.feedstockType || this.plantState.pathway;
    const h2Source = params.hydrogenSource || this.plantState.hydrogenSource;
    const volumeTonnes = params.annualVolumeTonnes || this.plantState.annualProductionTonnes;
    const targetBlendPct = params.blendPercentage || this.plantState.blendLimitPct;

    const ciValue = this.calculateCarbonIntensity(feedstock, h2Source);
    const reductionPct = this.calculateGhgReductionPercentage(ciValue);

    // Total Energy in Joules / MJ: Volume (tonnes) * 1,000 (kg/t) * 43.8 (MJ/kg)
    const totalEnergyMj = volumeTonnes * 1000.0 * this.jetEnergyDensityMjKg;
    const ciSavingsPerMj = (this.jetA1BaselineCi - ciValue); // gCO2e / MJ
    const totalCo2SavingsGrams = totalEnergyMj * ciSavingsPerMj;
    const annualCo2AbatedTonnes = Math.round(totalCo2SavingsGrams / 1000000.0);

    const corsiaEligible = reductionPct >= 10.0; // Minimum 10% CORSIA threshold

    return {
      netCarbonIntensity: ciValue,
      ghgReductionPct: reductionPct,
      annualCo2AbatedTonnes: annualCo2AbatedTonnes,
      corsiaEligible: corsiaEligible,
      corsiaStatus: corsiaEligible ? 'PASSED (CORSIA ELIGIBLE)' : 'NON-COMPLIANT'
    };
  }

  /**
   * Sanitizes input strings against HTML script injection
   * @param {string} str - Raw user input string
   * @returns {string} Clean sanitized string
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

// Node.js & Browser Export Compatibility
if (typeof module !== 'undefined' && module.exports) {
  module.exports = SafLifecycleEngine;
} else if (typeof window !== 'undefined') {
  window.SafLifecycleEngine = SafLifecycleEngine;

  // DOM Event Integration Initialization
  document.addEventListener('DOMContentLoaded', () => {
    const engine = new SafLifecycleEngine();

    const simBtn = document.getElementById('btn-run-saf-sim');
    if (simBtn) {
      simBtn.addEventListener('click', () => {
        const feedstock = document.getElementById('input-feedstock-type').value;
        const h2Source = document.getElementById('input-hydrogen-source').value;
        const volume = parseFloat(document.getElementById('input-annual-production').value);
        const blend = parseFloat(document.getElementById('input-blend-pct').value);

        const results = engine.simulateCorsiaLifecycle({
          feedstockType: feedstock,
          hydrogenSource: h2Source,
          annualVolumeTonnes: volume,
          blendPercentage: blend
        });

        document.getElementById('res-net-ci').textContent = `${results.netCarbonIntensity} gCO₂e/MJ`;
        document.getElementById('res-ghg-reduction').textContent = `${results.ghgReductionPct} %`;
        document.getElementById('res-annual-abatement').textContent = `${results.annualCo2AbatedTonnes.toLocaleString()} tCO₂e`;
        document.getElementById('res-corsia-status').textContent = results.corsiaStatus;
      });
    }

    const refreshBtn = document.getElementById('btn-trigger-refresh');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => {
        const valEl = document.getElementById('kpi-val-saf-output');
        if (valEl) {
          valEl.textContent = (1400 + Math.floor(Math.random() * 50)).toLocaleString();
        }
      });
    }
  });
}
