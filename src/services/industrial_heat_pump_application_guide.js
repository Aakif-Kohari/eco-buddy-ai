/**
 * High-Temperature Heat Pump (HTHP) Industrial Process Application Guide
 * Guidelines for replacing natural gas steam boilers across industrial sub-sectors.
 */

const HTHP_APPLICATION_GUIDE = [
  {
    sector: 'Food & Beverage Processing',
    targetProcess: 'Pasteurization, Sterilization, and Washing',
    tempRangeC: '80°C - 120°C',
    recommendedHeatPumpType: 'Single/Two-Stage Vapor Compression HTHP',
  },
  {
    sector: 'Pulp & Paper Manufacturing',
    targetProcess: 'Paper Web Drying & Evaporation',
    tempRangeC: '110°C - 150°C',
    recommendedHeatPumpType: 'Mechanical Vapor Recompression (MVR) / Steam HTHP',
  },
  {
    sector: 'Chemical & Pharmaceutical Industry',
    targetProcess: 'Distillation Columns & Reactor Jacket Heating',
    tempRangeC: '120°C - 160°C',
    recommendedHeatPumpType: 'High-Temperature Hybrid Absorption / Compression Heat Pump',
  },
];

module.exports = HTHP_APPLICATION_GUIDE;
