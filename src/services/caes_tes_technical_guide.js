/**
 * Adiabatic CAES Thermal Energy Storage (TES) Technical Specification Guide
 */

const CAES_TES_TECHNICAL_GUIDE = [
  {
    component: 'Thermal Energy Storage (TES) Medium',
    specification: 'Pressurized Hot Water / Molten Salt / Phase Change Material (PCM)',
    operatingTempC: '250°C - 550°C',
    purpose: 'Captures heat of air compression for reuse during expansion cycle, eliminating natural gas combustion.',
  },
  {
    component: 'High-Pressure Compressor Train',
    specification: 'Multi-stage radial/axial compressor with intercooling stage heat exchangers',
    pressureRating: 'Up to 80 bar',
    purpose: 'Compresses ambient air into underground salt cavern during off-peak renewable generation hours.',
  },
  {
    component: 'Air Expansion Turbine',
    specification: 'Multi-stage unheated/heated air expansion turbine',
    efficiencyRating: '88% Isentropic Efficiency',
    purpose: 'Expands high-pressure cavern air through turbine to generate dispatchable electrical power.',
  },
];

module.exports = CAES_TES_TECHNICAL_GUIDE;
