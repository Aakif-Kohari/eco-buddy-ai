/**
 * Industrial Refrigerant Properties & GWP Standard Catalog
 * Standards derived from F-Gas Regulation (EU) 517/2014 & ASHRAE 34 Safety Standards.
 */

const INDUSTRIAL_REFRIGERANT_CATALOG = [
  {
    refrigerantCode: 'R-1233zd(E)',
    chemicalName: 'Trans-1-chloro-3,3,3-trifluoropropene',
    gwp100Year: 1, // Ultra-low GWP Hydrofluoroolefin (HFO)
    ashraeSafetyClass: 'A1',
    maxDeliveryTempC: 160.0,
    criticalTempC: 166.5,
  },
  {
    refrigerantCode: 'R-717 (Ammonia)',
    chemicalName: 'Anhydrous Ammonia (NH3)',
    gwp100Year: 0, // Natural Refrigerant
    ashraeSafetyClass: 'B2L',
    maxDeliveryTempC: 95.0,
    criticalTempC: 132.4,
  },
  {
    refrigerantCode: 'R-744 (CO2)',
    chemicalName: 'Carbon Dioxide (Transcritical)',
    gwp100Year: 1, // Natural Refrigerant Baseline
    ashraeSafetyClass: 'A1',
    maxDeliveryTempC: 110.0,
    criticalTempC: 31.0,
  },
  {
    refrigerantCode: 'R-1336mzz(Z)',
    chemicalName: 'Cis-1,1,1,4,4,4-hexafluoro-2-butene',
    gwp100Year: 2, // Ultra-low GWP HFO
    ashraeSafetyClass: 'A1',
    maxDeliveryTempC: 175.0,
    criticalTempC: 171.3,
  },
];

module.exports = INDUSTRIAL_REFRIGERANT_CATALOG;
