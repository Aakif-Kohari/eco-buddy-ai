/**
 * Clinical & Industrial Water Quality Standards Reference Catalog
 * Standards derived from EPA Guidelines for Water Reuse & ISO 14046 Water Footprint Standard.
 */

const WATER_QUALITY_STANDARDS_CATALOG = [
  {
    category: 'Class A Urban Unrestricted Reuse',
    codMaxMgL: 30.0,
    bodMaxMgL: 10.0,
    tssMaxMgL: 5.0,
    turbidityMaxNtu: 2.0,
    disinfectionRequirement: 'UV + Free Chlorine Residual > 1.0 mg/L',
  },
  {
    category: 'Class B Restricted Agricultural Irrigation',
    codMaxMgL: 100.0,
    bodMaxMgL: 30.0,
    tssMaxMgL: 30.0,
    turbidityMaxNtu: 10.0,
    disinfectionRequirement: 'Secondary Treatment + Disinfection',
  },
  {
    category: 'Industrial Boiler Feed Ultra-Pure Water',
    codMaxMgL: 5.0,
    bodMaxMgL: 1.0,
    tssMaxMgL: 0.1,
    turbidityMaxNtu: 0.1,
    disinfectionRequirement: '2-Stage RO + Mixed Bed Deionization',
  },
  {
    category: 'Cooling Tower Makeup Water',
    codMaxMgL: 75.0,
    bodMaxMgL: 20.0,
    tssMaxMgL: 15.0,
    turbidityMaxNtu: 5.0,
    disinfectionRequirement: 'Biocide Shock Treatment + Scale Inhibitors',
  },
];

module.exports = WATER_QUALITY_STANDARDS_CATALOG;
