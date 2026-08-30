/**
 * Additional Unit Tests for Water Recycling Analytics Extension & Standards Catalog
 */

const { calculateSludgeProductionRate, evaluateChemicalDosingRates } = require('../src/services/water_recycling_analytics_extension');
const WATER_QUALITY_STANDARDS_CATALOG = require('../src/services/water_quality_standards_catalog');

describe('Water Recycling Analytics Extension Suite', () => {
  test('should accurately compute dry and wet sludge production rates', () => {
    const res = calculateSludgeProductionRate(10000, 120);
    expect(res.drySludgeKgDay).toBe(1200);
    expect(res.wetSludgeTonnesDay).toBe(6);
  });

  test('should accurately calculate alum and polymer chemical dosing requirements', () => {
    const res = evaluateChemicalDosingRates(10000);
    expect(res.alumCoagulantKgDay).toBe(250);
    expect(res.polymerFlocculantKgDay).toBe(20);
  });

  test('should load water quality standards catalog with 4 categories', () => {
    expect(WATER_QUALITY_STANDARDS_CATALOG.length).toBe(4);
    expect(WATER_QUALITY_STANDARDS_CATALOG[0].category).toBe('Class A Urban Unrestricted Reuse');
  });
});
