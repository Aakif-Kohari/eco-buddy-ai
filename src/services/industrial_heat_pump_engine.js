/**
 * Enterprise Architectural Specification:
 * Service: High-Temperature Industrial Heat Pump Decarbonization Engine
 * File: src/services/industrial_heat_pump_engine.js
 * Standard: ISO 50001 Energy Management Systems & Carnot Thermodynamic Cycle Performance
 * Scope: High-temperature industrial heat pump (HTHP) Coefficient of Performance (COP) modeling,
 *        waste heat recovery thermodynamic balance, and natural gas boiler replacement CO2 offset analytics.
 */

class IndustrialHeatPumpEngine {
  /**
   * Initialize Industrial Heat Pump Engine
   * @param {Object} config - Engine initialization parameters
   */
  constructor(config = {}) {
    this.facilityId = config.facilityId || 'FAC-HTHP-01';
    this.refrigerantType = config.refrigerantType || 'R-1233zd(E)'; // Low GWP Hydrofluoroolefin
    this.carnotEfficiencyFraction = config.carnotEfficiencyFraction || 0.55; // 55% Second-law efficiency

    // Facility State Telemetry
    this.facilityState = {
      wasteHeatSourceTempC: config.wasteHeatSourceTempC || 45.0, // Low-grade waste heat stream (45°C)
      requiredOutputTempC: config.requiredOutputTempC || 120.0,  // Process steam/hot water target (120°C)
      thermalLoadKw: config.thermalLoadKw || 5000,               // 5 MW thermal demand
      boilerEfficiencyPct: config.boilerEfficiencyPct || 85.0,   // Legacy natural gas boiler efficiency
    };
  }

  /**
   * Calculates Theoretical Carnot COP and Realistic Operating COP (Second Law Efficiency).
   * Formula: Carnot COP = T_sink_K / (T_sink_K - T_source_K)
   * Formula: Realistic COP = Carnot COP * CarnotEfficiencyFraction
   * @param {number} sourceTempC - Waste heat source temperature in °C
   * @param {number} sinkTempC - Target delivery temperature in °C
   * @returns {Object} Carnot & Realistic COP performance metrics
   */
  calculateCoefficientOfPerformance(sourceTempC = this.facilityState.wasteHeatSourceTempC, sinkTempC = this.facilityState.requiredOutputTempC) {
    if (sourceTempC >= sinkTempC) {
      throw new Error('Sink temperature must be strictly greater than source temperature.');
    }

    const sourceK = sourceTempC + 273.15;
    const sinkK = sinkTempC + 273.15;

    const carnotCop = sinkK / (sinkK - sourceK);
    const realisticCop = carnotCop * this.carnotEfficiencyFraction;

    return {
      sourceTempC,
      sinkTempC,
      temperatureLiftC: sinkTempC - sourceTempC,
      carnotCop: Math.round(carnotCop * 100) / 100,
      operatingCop: Math.round(realisticCop * 100) / 100,
    };
  }

  /**
   * Evaluates Electrical Power Demand and Waste Heat Recovery Thermal Balance.
   * @param {number} thermalLoadKw - Required process heat load in kW
   * @param {number} cop - Operating Coefficient of Performance
   * @returns {Object} Electrical power input and waste heat absorption rate
   */
  calculateEnergyBalance(thermalLoadKw = this.facilityState.thermalLoadKw, cop = null) {
    if (!cop) {
      const perf = this.calculateCoefficientOfPerformance();
      cop = perf.operatingCop;
    }

    // Thermal Load (Q_h) = Electrical Power (W_el) * COP
    const electricalPowerKw = thermalLoadKw / cop;
    const wasteHeatAbsorbedKw = thermalLoadKw - electricalPowerKw;

    return {
      requiredThermalOutputKw: thermalLoadKw,
      electricalPowerInputKw: Math.round(electricalPowerKw),
      wasteHeatAbsorbedKw: Math.round(wasteHeatAbsorbedKw),
      operatingCop: cop,
    };
  }

  /**
   * Computes Natural Gas Boiler Replacement Carbon Offset & OPEX Savings.
   * @param {number} operatingHoursPerYear - Annual operational hours (default 8000 hrs)
   * @param {number} gridEmissionFactorKgCo2Kwh - Grid carbon intensity (default 0.420 kg/kWh)
   * @param {number} naturalGasEmissionFactorKgCo2Kwh - Gas carbon intensity (default 0.202 kg/kWh)
   * @returns {Object} Decarbonization and cost-benefit metrics
   */
  evaluateDecarbonizationImpact(
    operatingHoursPerYear = 8000,
    gridEmissionFactorKgCo2Kwh = 0.420,
    naturalGasEmissionFactorKgCo2Kwh = 0.202
  ) {
    const balance = this.calculateEnergyBalance();
    
    // Legacy Boiler Natural Gas Energy Required = Thermal Load / Boiler Efficiency
    const boilerGasKw = this.facilityState.thermalLoadKw / (this.facilityState.boilerEfficiencyPct / 100);
    const annualGasConsumptionKwh = boilerGasKw * operatingHoursPerYear;
    const annualBoilerCo2Tonnes = (annualGasConsumptionKwh * naturalGasEmissionFactorKgCo2Kwh) / 1000;

    // HTHP Grid Electricity Consumption
    const annualHthpElectricityKwh = balance.electricalPowerInputKw * operatingHoursPerYear;
    const annualHthpCo2Tonnes = (annualHthpElectricityKwh * gridEmissionFactorKgCo2Kwh) / 1000;

    const netCo2OffsetTonnes = annualBoilerCo2Tonnes - annualHthpCo2Tonnes;

    return {
      legacyBoilerCo2TonnesYear: Math.round(annualBoilerCo2Tonnes),
      hthpElectrifiedCo2TonnesYear: Math.round(annualHthpCo2Tonnes),
      netAnnualCo2OffsetTonnes: Math.round(netCo2OffsetTonnes),
      decarbonizationPct: Math.round((netCo2OffsetTonnes / annualBoilerCo2Tonnes) * 100),
    };
  }
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = IndustrialHeatPumpEngine;
} else if (typeof window !== 'undefined') {
  window.IndustrialHeatPumpEngine = IndustrialHeatPumpEngine;
}
