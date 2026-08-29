/**
 * Enterprise Architectural Specification & Header:
 * Module: Green Hydrogen Production & Electrolyzer Analytics Engine
 * File: src/services/hydrogen_electrolyzer_engine.js
 * Standard: ECMAScript 2022 Class Specification, ISO 22734 Hydrogen Generator Standards
 * Scope: Faraday's Law Electrolysis Yield, Specific Power Consumption (SEC), Levelized Cost of Hydrogen (LCOH),
 *        Stack Degradation Telemetry, and Steam Methane Reforming (SMR) Carbon Abatement Accounting.
 *
 * Technical Specifications:
 * - Faraday's Law Hydrogen Mass Flow: m_H2 = (I * N_cells * M_H2) / (z * F) * η_faradaic
 * - Faraday Constant F = 96485.33 C/mol, Lower Heating Value LHV H2 = 33.33 kWh/kg (120 MJ/kg)
 * - Specific Energy Consumption (SEC): SEC = Power_Stack_kW / Mass_Flow_H2_kg_h
 * - LHV Stack Efficiency: η_LHV = (LHV_H2 / SEC) * 100%
 */

class HydrogenElectrolyzerEngine {
  /**
   * Initialize Hydrogen Electrolyzer Engine with default thermodynamic constants & plant configs
   * @param {Object} config - Engine initialization configuration object
   */
  constructor(config = {}) {
    this.faradayConstant = 96485.33; // Coulombs / mol
    this.molarMassH2 = 2.01588e-3; // kg / mol
    this.lhvHydrogenKwhKg = 33.33; // LHV kWh per kg H2
    this.hhvHydrogenKwhKg = 39.41; // HHV kWh per kg H2
    this.baselineSmrEmissions = 9.3; // kg CO2e per kg H2 (Grey Hydrogen baseline)

    // Plant Default Configuration Model
    this.plantState = {
      plantId: config.plantId || 'PLANT-PEM-100',
      technologyType: config.technologyType || 'PEM', // PEM, AWE, SOEC
      stackCount: config.stackCount || 10,
      cellsPerStack: config.cellsPerStack || 120,
      activeAreaCm2: config.activeAreaCm2 || 1500,
      maxCurrentDensity: config.maxCurrentDensity || 2.5, // A/cm²
      nominalPowerMw: config.nominalPowerMw || 100.0,
      faradaicEfficiency: config.faradaicEfficiency || 0.985, // 98.5%
      waterConsumptionRate: config.waterConsumptionRate || 9.8 // Liters deionised H2O per kg H2
    };

    this.telemetryCache = new Map();
    this.initDefaultTelemetry();
  }

  /**
   * Initializes default mock telemetry streams for connected Electrolyzer Stacks
   */
  initDefaultTelemetry() {
    this.telemetryCache.set('STACK-01', {
      id: 'STACK-01',
      tech: 'PEM',
      currentDensityAcm2: 2.45,
      avgCellVoltage: 1.82,
      temperatureCelsius: 68.4,
      purityPct: 99.999,
      operatingHours: 8420,
      status: 'OPERATIONAL'
    });

    this.telemetryCache.set('STACK-02', {
      id: 'STACK-02',
      tech: 'PEM',
      currentDensityAcm2: 2.38,
      avgCellVoltage: 1.94,
      temperatureCelsius: 71.2,
      purityPct: 99.998,
      operatingHours: 14200,
      status: 'OPERATIONAL'
    });
  }

  /**
   * Calculates Hydrogen Mass Production Rate in kg/h using Faraday's Law
   * Formula: m_H2 (kg/s) = (I * N_cells * M_H2) / (z * F) * η_faradaic
   * @param {number} currentAmperes - Total stack operating current (Amperes)
   * @param {number} cellCount - Total number of series cells in stack
   * @param {number} faradaicEff - Faradaic Efficiency fraction (0.90 - 0.999)
   * @returns {number} Hydrogen mass flow rate in kg/hour
   */
  calculateFaradayHydrogenYield(currentAmperes, cellCount = 120, faradaicEff = 0.985) {
    if (typeof currentAmperes !== 'number' || currentAmperes < 0) {
      throw new Error('Current must be a non-negative number.');
    }

    const valencyZ = 2; // 2 electrons per H2 molecule
    const massFlowKgPerSec = (currentAmperes * cellCount * this.molarMassH2 * faradaicEff) / (valencyZ * this.faradayConstant);
    const massFlowKgPerHour = massFlowKgPerSec * 3600;

    return parseFloat(massFlowKgPerHour.toFixed(3));
  }

  /**
   * Calculates Specific Energy Consumption (SEC) and LHV Stack Efficiency
   * @param {number} totalPowerMw - Total DC/AC power input to electrolyzer (MW)
   * @param {number} h2YieldKgH - Hourly hydrogen production rate (kg/h)
   * @returns {Object} Specific power metrics and thermal efficiency
   */
  calculateSpecificEnergyConsumption(totalPowerMw, h2YieldKgH) {
    if (h2YieldKgH <= 0) {
      throw new Error('Hydrogen yield must be strictly greater than 0 kg/h.');
    }

    const totalPowerKw = totalPowerMw * 1000.0;
    const secKwhPerKg = totalPowerKw / h2YieldKgH;
    const lhvEfficiencyPct = (this.lhvHydrogenKwhKg / secKwhPerKg) * 100.0;

    return {
      secKwhPerKg: parseFloat(secKwhPerKg.toFixed(2)),
      lhvEfficiencyPct: parseFloat(lhvEfficiencyPct.toFixed(1)),
      hhvEfficiencyPct: parseFloat(((this.hhvHydrogenKwhKg / secKwhPerKg) * 100.0).toFixed(1))
    };
  }

  /**
   * Computes Levelized Cost of Hydrogen (LCOH) in $/kg and Annual Decarbonization Abatement
   * @param {Object} params - Financial and Operational Parameters Override
   * @returns {Object} Comprehensive LCOH calculation breakdown
   */
  simulateLcohAndAbatement(params = {}) {
    const powerMw = params.powerInputMw || this.plantState.nominalPowerMw;
    const powerCostMwh = params.electricityCostPerMwh || 38.50;
    const stackEffLhv = params.stackEfficiencyLhvPct || 66.5;

    // Derived SEC from efficiency: SEC = LHV / (Eff / 100)
    const secKwhKg = this.lhvHydrogenKwhKg / (stackEffLhv / 100.0);
    const hourlyProductionKg = (powerMw * 1000.0) / secKwhKg;

    // Cost Components
    const electricityCostPerKg = (secKwhKg * powerCostMwh) / 1000.0;
    const waterCostPerKg = (this.plantState.waterConsumptionRate * 0.003); // $0.003 per liter DI H2O
    const capexOpexAmortizationPerKg = 0.65; // Fixed plant amortization ($/kg)

    const totalLcohPerKg = electricityCostPerKg + waterCostPerKg + capexOpexAmortizationPerKg;

    // Environmental Abatement vs SMR Grey H2
    const dailyH2Kg = hourlyProductionKg * 24;
    const dailyCo2AbatedTonnes = (dailyH2Kg * this.baselineSmrEmissions) / 1000.0;
    const annualCo2AbatedTonnes = dailyCo2AbatedTonnes * 365;

    return {
      hourlyH2YieldKg: Math.round(hourlyProductionKg),
      secKwhPerKg: parseFloat(secKwhKg.toFixed(2)),
      lcohDollarsPerKg: parseFloat(totalLcohPerKg.toFixed(2)),
      annualCo2AbatedTonnes: Math.round(annualCo2AbatedTonnes)
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
  module.exports = HydrogenElectrolyzerEngine;
} else if (typeof window !== 'undefined') {
  window.HydrogenElectrolyzerEngine = HydrogenElectrolyzerEngine;

  // DOM Event Integration Initialization
  document.addEventListener('DOMContentLoaded', () => {
    const engine = new HydrogenElectrolyzerEngine();

    const simBtn = document.getElementById('btn-run-lcoh-sim');
    if (simBtn) {
      simBtn.addEventListener('click', () => {
        const powerMw = parseFloat(document.getElementById('input-power-input').value);
        const effLhv = parseFloat(document.getElementById('input-stack-efficiency').value);
        const tariff = parseFloat(document.getElementById('input-electricity-cost').value);

        const results = engine.simulateLcohAndAbatement({
          powerInputMw: powerMw,
          stackEfficiencyLhvPct: effLhv,
          electricityCostPerMwh: tariff
        });

        document.getElementById('res-h2-output').textContent = `${results.hourlyH2YieldKg.toLocaleString()} kg/h`;
        document.getElementById('res-sec-val').textContent = `${results.secKwhPerKg} kWh/kg`;
        document.getElementById('res-lcoh-val').textContent = `$${results.lcohDollarsPerKg} / kg`;
        document.getElementById('res-annual-abatement').textContent = `${results.annualCo2AbatedTonnes.toLocaleString()} tCO₂e`;
      });
    }

    const refreshBtn = document.getElementById('btn-trigger-refresh');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => {
        const valEl = document.getElementById('kpi-val-h2-output');
        if (valEl) {
          valEl.textContent = (1800 + Math.floor(Math.random() * 80)).toLocaleString();
        }
      });
    }
  });
}
