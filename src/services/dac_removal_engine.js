/**
 * Enterprise Architectural Specification & Header:
 * Module: Direct Air Capture (DAC) & Carbon Removal Core Service Engine
 * File: src/services/dac_removal_engine.js
 * Standard: ECMAScript 2022 Class Specification, ISO 14064 Carbon Accounting, Puro.earth CDR Standard
 * Scope: Solid-Sorbent & Liquid-Solvent CO2 Extraction, Thermal Desorption Energy Balances,
 *        Parasitic Energy Penalty Calculation, Net Carbon Removal Efficiency, and CORC Credit Issuance.
 *
 * Technical Specifications:
 * - Specific Thermal Energy Consumption: E_thermal (GJ/tCO2) = Heat_Input_GJ / CO2_Gross_Captured_tonnes
 * - Parasitic Emissions Penalty: CO2_parasitic = E_thermal * Grid_EF + E_electric * Grid_EF
 * - Net CDR Efficiency: Net_Efficiency (%) = ((CO2_gross - CO2_parasitic) / CO2_gross) * 100%
 * - Puro.earth CORCs Issued: CORCs = Math.floor(CO2_net_tonnes)
 */

class DacRemovalEngine {
  /**
   * Initialize DAC Engine with default thermodynamic constants & plant state
   * @param {Object} config - Engine initialization configuration object
   */
  constructor(config = {}) {
    this.ambientCo2Ppm = 420.0; // Ambient atmospheric CO2 baseline ppm
    this.molarMassCo2 = 44.01; // g / mol
    this.co2DensityKgM3 = 1.977; // kg / m3 at STP

    // Plant Default Configuration Model
    this.plantState = {
      plantId: config.plantId || 'DAC-SOLID-100',
      technologyType: config.technologyType || 'SOLID_AMINE', // SOLID_AMINE, LIQUID_SOLVENT
      collectorBlockCount: config.collectorBlockCount || 12,
      fanFlowRateCfm: config.fanFlowRateCfm || 420000,
      desorptionTempCelsius: config.desorptionTempCelsius || 98.4,
      desorptionVacuumBar: config.desorptionVacuumBar || 0.18,
      grossDailyTargetTonnes: config.grossDailyTargetTonnes || 1000.0,
      heatSource: config.heatSource || 'GEOTHERMAL' // GEOTHERMAL, WASTE_HEAT, HEAT_PUMP
    };

    // Energy Source Emission Factors (gCO2e / MJ)
    this.heatSourceEmissionFactor = {
      'GEOTHERMAL': 0.0,
      'WASTE_HEAT': 0.0,
      'HEAT_PUMP': 15.0
    };

    this.telemetryCache = new Map();
    this.initDefaultTelemetry();
  }

  /**
   * Initializes default mock telemetry streams for connected Collector Blocks
   */
  initDefaultTelemetry() {
    this.telemetryCache.set('BLOCK-01', {
      id: 'BLOCK-01',
      mode: 'ADSORPTION',
      fanCfm: 420000,
      co2LoadingMmolG: 1.82,
      temperatureC: 24.5,
      saturationPct: 84.2,
      status: 'OPERATIONAL'
    });

    this.telemetryCache.set('BLOCK-02', {
      id: 'BLOCK-02',
      mode: 'DESORPTION',
      steamTempC: 98.4,
      vacuumBar: 0.18,
      offgasPurityPct: 99.8,
      cycleRemainingMin: 32,
      status: 'OPERATIONAL'
    });
  }

  /**
   * Calculates Specific Thermal Energy Consumption in GJ per tonne CO2 captured
   * @param {number} totalHeatGj - Total thermal heat energy input (GJ)
   * @param {number} grossCo2CapturedTonnes - Gross mass of CO2 desorbed (tonnes)
   * @returns {number} Specific thermal energy in GJ / tCO2
   */
  calculateSpecificThermalEnergy(totalHeatGj, grossCo2CapturedTonnes) {
    if (grossCo2CapturedTonnes <= 0) {
      throw new Error('Gross CO2 captured must be strictly greater than 0 tonnes.');
    }

    const specificEnergyGjPerTonne = totalHeatGj / grossCo2CapturedTonnes;
    return parseFloat(specificEnergyGjPerTonne.toFixed(2));
  }

  /**
   * Calculates Parasitic Emissions and Net Carbon Removal Efficiency (%)
   * Formula: Net_Efficiency = ((CO2_gross - CO2_parasitic) / CO2_gross) * 100%
   * @param {number} grossCo2Tonnes - Gross daily captured CO2 mass (tonnes)
   * @param {number} thermalGjPerTonne - Specific thermal requirement (GJ/tCO2)
   * @param {string} heatSourceKey - Energy source key ('GEOTHERMAL', 'WASTE_HEAT', 'HEAT_PUMP')
   * @returns {Object} Net CDR metrics and efficiency percentage
   */
  calculateNetCdrEfficiency(grossCo2Tonnes = 1000.0, thermalGjPerTonne = 5.5, heatSourceKey = 'GEOTHERMAL') {
    if (grossCo2Tonnes <= 0) {
      throw new Error('Gross CO2 mass must be positive.');
    }

    const heatEfGco2PerMj = this.heatSourceEmissionFactor[heatSourceKey] !== undefined ? this.heatSourceEmissionFactor[heatSourceKey] : 0.0;
    
    // Thermal energy in MJ per tonne: GJ * 1,000 MJ/GJ
    const thermalMjPerTonne = thermalGjPerTonne * 1000.0;
    const thermalEmissionsGramsPerTonne = thermalMjPerTonne * heatEfGco2PerMj;
    
    // Auxiliary fan electrical consumption (~1.2 GJ_elec / tCO2) @ 20 gCO2e/MJ grid
    const electricEmissionsGramsPerTonne = 1.2 * 1000.0 * 20.0; 

    const totalParasiticGramsPerTonne = thermalEmissionsGramsPerTonne + electricEmissionsGramsPerTonne;
    const totalParasiticTonnesPerTonne = totalParasiticGramsPerTonne / 1000000.0;

    const totalParasiticLossTonnes = grossCo2Tonnes * totalParasiticTonnesPerTonne;
    const netCdrTonnes = Math.max(0, grossCo2Tonnes - totalParasiticLossTonnes);
    const netEfficiencyPct = (netCdrTonnes / grossCo2Tonnes) * 100.0;

    return {
      grossCo2Tonnes: grossCo2Tonnes,
      parasiticLossTonnes: parseFloat(totalParasiticLossTonnes.toFixed(1)),
      netCdrTonnes: parseFloat(netCdrTonnes.toFixed(1)),
      netEfficiencyPct: parseFloat(netEfficiencyPct.toFixed(1))
    };
  }

  /**
   * Simulates Net Carbon Dioxide Removal (CDR) and Puro.earth CORC Issuance
   * @param {Object} params - Simulation Parameters Override
   * @returns {Object} Complete CDR simulation results
   */
  simulateNetCdrAndCorcs(params = {}) {
    const grossCap = params.grossCaptureTonnes || this.plantState.grossDailyTargetTonnes;
    const thermalReq = params.thermalReqGjPerTonne || 5.5;
    const heatSource = params.heatSource || this.plantState.heatSource;

    const netCdrMetrics = this.calculateNetCdrEfficiency(grossCap, thermalReq, heatSource);
    
    const dailyNetCdrTonnes = netCdrMetrics.netCdrTonnes;
    const annualNetCdrTonnes = dailyNetCdrTonnes * 365;
    const annualCorcs = Math.floor(annualNetCdrTonnes);

    return {
      netDailyCdrTonnes: dailyNetCdrTonnes,
      parasiticLossTonnes: netCdrMetrics.parasiticLossTonnes,
      netEfficiencyPct: netCdrMetrics.netEfficiencyPct,
      annualCorcsIssued: annualCorcs
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
  module.exports = DacRemovalEngine;
} else if (typeof window !== 'undefined') {
  window.DacRemovalEngine = DacRemovalEngine;

  // DOM Event Integration Initialization
  document.addEventListener('DOMContentLoaded', () => {
    const engine = new DacRemovalEngine();

    const simBtn = document.getElementById('btn-run-dac-sim');
    if (simBtn) {
      simBtn.addEventListener('click', () => {
        const grossCap = parseFloat(document.getElementById('input-gross-capture').value);
        const thermalReq = parseFloat(document.getElementById('input-thermal-req').value);
        const heatSource = document.getElementById('input-heat-source').value;

        const results = engine.simulateNetCdrAndCorcs({
          grossCaptureTonnes: grossCap,
          thermalReqGjPerTonne: thermalReq,
          heatSource: heatSource
        });

        document.getElementById('res-net-cdr').textContent = `${results.netDailyCdrTonnes} tCO₂ / day`;
        document.getElementById('res-parasitic-loss').textContent = `${results.parasiticLossTonnes} tCO₂ / day`;
        document.getElementById('res-net-efficiency').textContent = `${results.netEfficiencyPct} %`;
        document.getElementById('res-annual-corcs').textContent = `${results.annualCorcsIssued.toLocaleString()} CORCs`;
      });
    }

    const refreshBtn = document.getElementById('btn-trigger-refresh');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => {
        const valEl = document.getElementById('kpi-val-captured');
        if (valEl) {
          valEl.textContent = (1200 + Math.floor(Math.random() * 60)).toLocaleString();
        }
      });
    }
  });
}
