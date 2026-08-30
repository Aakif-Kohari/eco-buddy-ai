/**
 * Global Compressed Air Energy Storage (CAES) Geological Cavern Catalog
 * Reference catalog of geological formations suitable for grid-scale CAES.
 */

const CAES_CAVERN_CATALOG = [
  {
    cavernType: 'Solution-Mined Salt Cavern',
    geologicalSuitability: 'EXCELLENT',
    maxPressureBar: 80.0,
    typicalVolumeM3: 300000,
    airTightnessRating: 'HERMETIC_SEAL',
    exampleFacility: 'Huntorf CAES (Germany) / McIntosh CAES (USA)',
  },
  {
    cavernType: 'Depleted Natural Gas Reservoir',
    geologicalSuitability: 'GOOD',
    maxPressureBar: 60.0,
    typicalVolumeM3: 1500000,
    airTightnessRating: 'HIGH_INTEGRITY',
    exampleFacility: 'Pio de las Brisas (Spain)',
  },
  {
    cavernType: 'Hard-Rock Mined Cavern (Lined)',
    geologicalSuitability: 'VERY_GOOD',
    maxPressureBar: 70.0,
    typicalVolumeM3: 200000,
    airTightnessRating: 'STEEL_MEMBRANE_LINED',
    exampleFacility: 'Goderich A-CAES (Canada)',
  },
  {
    cavernType: 'Porous Aquifer Formation',
    geologicalSuitability: 'MODERATE',
    maxPressureBar: 50.0,
    typicalVolumeM3: 2000000,
    airTightnessRating: 'NATURAL_CAPROCK',
    exampleFacility: 'Pittsfield Aquifer Test (USA)',
  },
];

module.exports = CAES_CAVERN_CATALOG;
