/**
 * Thermoelectric Semiconductor Materials & Figure of Merit (ZT) Catalog
 * Reference catalog based on solid-state energy conversion literature.
 */

const THERMOELECTRIC_MATERIALS_CATALOG = [
  {
    materialName: 'Bismuth Telluride (Bi2Te3)',
    operatingTempRangeC: '20°C - 250°C',
    averageZt: 1.1,
    typicalApplications: 'Low-to-medium temperature industrial exhaust & electronics cooling',
    seebeckCoeffUvK: 210,
  },
  {
    materialName: 'Lead Telluride (PbTe)',
    operatingTempRangeC: '250°C - 500°C',
    averageZt: 1.4,
    typicalApplications: 'Medium-to-high temperature furnace waste heat recovery',
    seebeckCoeffUvK: 240,
  },
  {
    materialName: 'Silicon Germanium (SiGe)',
    operatingTempRangeC: '600°C - 1000°C',
    averageZt: 0.9,
    typicalApplications: 'High-temperature industrial kilns & deep-space RTGs',
    seebeckCoeffUvK: 180,
  },
  {
    materialName: 'Skutterudites (CoSb3)',
    operatingTempRangeC: '300°C - 600°C',
    averageZt: 1.3,
    typicalApplications: 'Automotive exhaust gas energy harvesting',
    seebeckCoeffUvK: 220,
  },
];

module.exports = THERMOELECTRIC_MATERIALS_CATALOG;
