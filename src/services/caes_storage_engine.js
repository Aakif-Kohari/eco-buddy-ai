/**
 * Enterprise Architectural Specification:
 * Service: Adiabatic Compressed Air Energy Storage (A-CAES) Performance Engine
 * File: src/services/caes_storage_engine.js
 * Standard: ISO 50001 Energy Management Systems & Thermodynamic Ideal Gas Compression Modeling
 * Scope: Multi-stage intercooled air compression, cavern pressure dynamics (bar), Thermal Energy Storage (TES)
 *        heat exchanger efficiency, and grid-scale round-trip efficiency (RTE) calculations.
 */

class CaesStorageEngine {
  /**
   * Initialize CAES Storage Engine
   * @param {Object} config - Engine configuration options
   */
  constructor(config = {}) {
    this.facilityId = config.facilityId || 'CAES-FAC-01';
    this.cavernVolumeM3 = config.cavernVolumeM3 || 300000; // Salt cavern volume (300,000 m³)
    this.compressionStagesCount = config.compressionStagesCount || 4;
    this.heatExchangerEfficiency = config.heatExchangerEfficiency || 0.92; // TES thermal recovery efficiency

    // Cavern Operating Pressure Range (bar)
    this.pressureMinBar = config.pressureMinBar || 45.0; // Minimum discharge cavern pressure
    this.pressureMaxBar = config.pressureMaxBar || 75.0; // Maximum fully charged cavern pressure

    // Facility Operating State
    this.facilityState = {
      currentCavernPressureBar: config.initialPressureBar || 52.0,
      storedThermalEnergyMWh: config.initialThermalMWh || 120.0,
      operatingMode: 'IDLE', // 'CHARGING', 'DISCHARGING', 'IDLE'
    };
  }

  /**
   * Calculates Multi-Stage Compression Power and Thermal Heat Capture Rate.
   * Formula: W_comp = N * (k / (k - 1)) * m_dot * R * T_in * [ (P_out / P_in)^((k-1)/(N*k)) - 1 ]
   * @param {number} airMassFlowKgSec - Mass flow rate of air during compression (kg/s)
   * @param {number} compressionRatioTotal - Overall pressure ratio (P_max / P_ambient)
   * @returns {Object} Compression power requirements and thermal heat recovery rate
   */
  calculateCompressionPerformance(airMassFlowKgSec = 150.0, compressionRatioTotal = 75.0) {
    if (airMassFlowKgSec <= 0) {
      throw new Error('Air mass flow rate must be a positive number.');
    }

    const k = 1.4; // Isentropic expansion factor for air
    const rGas = 0.287; // kJ/(kg·K)
    const tInK = 298.15; // 25°C ambient air temperature
    const n = this.compressionStagesCount;

    const pressureRatioPerStage = Math.pow(compressionRatioTotal, 1 / n);
    const exponent = (k - 1) / (k * n);
    
    // Compressor power in MW
    const powerMw = (n * (k / (k - 1)) * airMassFlowKgSec * rGas * tInK * (Math.pow(compressionRatioTotal, exponent) - 1)) / 1000;
    
    // Recoverable thermal energy rate (MW)
    const thermalRecoveredMw = powerMw * 0.42 * this.heatExchangerEfficiency;

    return {
      airMassFlowKgSec,
      stagesCount: n,
      pressureRatioPerStage: Math.round(pressureRatioPerStage * 100) / 100,
      compressorPowerMW: Math.round(powerMw * 100) / 100,
      thermalHeatCapturedMW: Math.round(thermalRecoveredMw * 100) / 100,
    };
  }

  /**
   * Calculates Isothermal Cavern Pressure Growth during Charging.
   * Formula: ΔP = (m_added * R * T) / V_cavern
   * @param {number} chargingHours - Duration of charging cycle in hours
   * @param {number} airMassFlowKgSec - Air mass flow rate (kg/s)
   * @returns {Object} Updated cavern pressure state
   */
  simulateChargingCycle(chargingHours = 6.0, airMassFlowKgSec = 150.0) {
    const totalMassKg = airMassFlowKgSec * 3600 * chargingHours;
    const rGas = 287; // J/(kg·K)
    const tK = 313.15; // 40°C cavern air temperature

    const pressureRisePa = (totalMassKg * rGas * tK) / this.cavernVolumeM3;
    const pressureRiseBar = pressureRisePa / 100000;

    const newPressureBar = Math.min(this.pressureMaxBar, this.facilityState.currentCavernPressureBar + pressureRiseBar);
    this.facilityState.currentCavernPressureBar = Math.round(newPressureBar * 10) / 10;
    this.facilityState.operatingMode = 'CHARGING';

    return {
      chargingHours,
      airAddedTonnes: Math.round(totalMassKg / 1000),
      pressureRiseBar: Math.round(pressureRiseBar * 10) / 10,
      newCavernPressureBar: this.facilityState.currentCavernPressureBar,
      isFullyCharged: this.facilityState.currentCavernPressureBar >= this.pressureMaxBar,
    };
  }

  /**
   * Computes Adiabatic CAES Round-Trip Efficiency (RTE).
   * Formula: RTE = E_discharged_electric / E_charged_electric
   * @param {number} expansionEfficiency - Air turbine expansion efficiency (default 0.88)
   * @returns {Object} Storage capacity and grid-scale round-trip efficiency
   */
  evaluateRoundTripEfficiency(expansionEfficiency = 0.88) {
    // Adiabatic CAES with TES achieves 65% - 75% Round-Trip Efficiency
    const baseCompressorEfficiency = 0.85;
    const rtePct = baseCompressorEfficiency * expansionEfficiency * (0.85 + 0.15 * this.heatExchangerEfficiency);

    const maxStorageCapacityMWh = 1200; // 1.2 GWh storage capacity

    return {
      storageCapacityMWh: maxStorageCapacityMWh,
      cavernVolumeM3: this.cavernVolumeM3,
      heatExchangerEfficiencyPct: Math.round(this.heatExchangerEfficiency * 100),
      roundTripEfficiencyPct: Math.round(rtePct * 1000) / 10,
      gridDecarbonizationGrade: rtePct >= 0.70 ? 'A+' : 'A',
    };
  }
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = CaesStorageEngine;
} else if (typeof window !== 'undefined') {
  window.CaesStorageEngine = CaesStorageEngine;
}
