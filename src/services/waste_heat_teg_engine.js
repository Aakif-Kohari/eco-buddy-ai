/**
 * Enterprise Architectural Specification:
 * Service: Waste Heat Thermoelectric Generator (TEG) Energy Harvesting Engine
 * File: src/services/waste_heat_teg_engine.js
 * Standard: Seebeck Effect Solid-State Energy Conversion & ISO 50001 Energy Management Systems
 * Scope: High-temperature exhaust gas waste heat recovery, Seebeck coefficient (S) voltage generation,
 *        Figure of Merit (ZT) optimization, and parasitic electrical power harvest analytics.
 */

class WasteHeatTegEngine {
  /**
   * Initialize Waste Heat Thermoelectric Generator Engine
   * @param {Object} config - Engine configuration options
   */
  constructor(config = {}) {
    this.facilityId = config.facilityId || 'TEG-HARVEST-01';
    this.semiconductorMaterial = config.semiconductorMaterial || 'Bismuth Telluride (Bi2Te3)';
    this.seebeckCoefficientUvK = config.seebeckCoefficientUvK || 210; // µV/K per couple
    this.thermocoupleCouplesCount = config.thermocoupleCouplesCount || 1000;

    // Facility Waste Heat Flue Gas Baseline Telemetry
    this.facilityState = {
      hotSideExhaustTempC: config.hotSideExhaustTempC || 350.0, // Flue gas hot side (350°C)
      coldSideCoolantTempC: config.coldSideCoolantTempC || 40.0, // Water-cooled cold side (40°C)
      internalResistanceOhms: config.internalResistanceOhms || 2.5, // TEG module internal resistance
      loadResistanceOhms: config.loadResistanceOhms || 2.5, // Matched load resistance for maximum power transfer
    };
  }

  /**
   * Calculates Open-Circuit Seebeck Voltage (V_oc) and Temperature Delta (ΔT).
   * Formula: V_oc = N * S * (T_hot - T_cold)
   * @param {number} hotTempC - Hot side exhaust temperature in °C
   * @param {number} coldTempC - Cold side coolant temperature in °C
   * @returns {Object} Open-circuit voltage and temperature gradient
   */
  calculateSeebeckVoltage(hotTempC = this.facilityState.hotSideExhaustTempC, coldTempC = this.facilityState.coldSideCoolantTempC) {
    if (hotTempC <= coldTempC) {
      throw new Error('Hot side temperature must be strictly greater than cold side temperature.');
    }

    const tempDeltaC = hotTempC - coldTempC;
    const seebeckVoltsPerKelvin = (this.seebeckCoefficientUvK * 1e-6) * this.thermocoupleCouplesCount;
    const openCircuitVoltage = seebeckVoltsPerKelvin * tempDeltaC;

    return {
      hotSideTempC: hotTempC,
      coldSideTempC: coldTempC,
      tempDeltaC,
      openCircuitVoltageVolts: Math.round(openCircuitVoltage * 100) / 100,
    };
  }

  /**
   * Calculates Maximum Power Transfer Output (P_max) under Impedance Matched Load.
   * Formula: P_max = (V_oc^2) / (4 * R_internal)
   * @returns {Object} Maximum electrical power output and current yield
   */
  calculatePowerOutput() {
    const voltageMetrics = this.calculateSeebeckVoltage();
    const vOc = voltageMetrics.openCircuitVoltageVolts;
    const rInt = this.facilityState.internalResistanceOhms;

    const maxPowerWatts = (vOc * vOc) / (4 * rInt);
    const loadCurrentAmps = vOc / (2 * rInt);

    return {
      openCircuitVoltageVolts: vOc,
      operatingVoltageVolts: Math.round((vOc / 2) * 100) / 100,
      loadCurrentAmps: Math.round(loadCurrentAmps * 100) / 100,
      maxElectricalPowerWatts: Math.round(maxPowerWatts * 10) / 10,
    };
  }

  /**
   * Computes Dimensionless Thermoelectric Figure of Merit (ZT) and Conversion Efficiency.
   * Formula: ZT = (S^2 * σ / κ) * T_avg
   * @param {number} ztValue - Dimensionless figure of merit (default 1.1)
   * @returns {Object} Efficiency percentage and harvested daily energy (kWh)
   */
  evaluateConversionEfficiency(ztValue = 1.1) {
    const voltage = this.calculateSeebeckVoltage();
    const power = this.calculatePowerOutput();

    const tHotK = voltage.hotSideTempC + 273.15;
    const tColdK = voltage.coldSideTempC + 273.15;
    const tAvgK = (tHotK + tColdK) / 2;

    const carnotEff = (tHotK - tColdK) / tHotK;
    const gamma = Math.sqrt(1 + ztValue * (tAvgK / 300));
    const thermalEfficiency = carnotEff * ((gamma - 1) / (gamma + (tColdK / tHotK)));

    const dailyHarvestKwh = (power.maxElectricalPowerWatts * 24) / 1000;

    return {
      dimensionlessZt: ztValue,
      carnotLimitPct: Math.round(carnotEff * 1000) / 10,
      netThermalToElectricEfficiencyPct: Math.round(thermalEfficiency * 1000) / 10,
      dailyEnergyHarvestedKwh: Math.round(dailyHarvestKwh * 100) / 100,
    };
  }
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = WasteHeatTegEngine;
} else if (typeof window !== 'undefined') {
  window.WasteHeatTegEngine = WasteHeatTegEngine;
}
