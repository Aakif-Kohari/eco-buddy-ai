/**
 * Seebeck Effect & Thermoelectric Generator Technical Guide Catalog
 */

const SEEBECK_TECHNICAL_GUIDE = [
  {
    topic: 'Seebeck Coefficient (S)',
    description: 'Magnitude of induced thermoelectric voltage in response to a temperature difference across a material.',
    unit: 'µV/K',
  },
  {
    topic: 'Impedance Matching Rule',
    description: 'Maximum power transfer occurs when internal electrical resistance equals external load resistance (R_load = R_int).',
    unit: 'Ohms (Ω)',
  },
  {
    topic: 'Figure of Merit (ZT)',
    description: 'Measure of material performance: ZT = (S^2 * σ / κ) * T_avg. Higher values indicate higher thermodynamic efficiency.',
    unit: 'Dimensionless',
  },
];

module.exports = SEEBECK_TECHNICAL_GUIDE;
