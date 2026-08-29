/**
 * Unit & Integration Test Suite for Industrial Heat Pump Engine
 * Tests Carnot COP calculations, electrical power demand, and boiler replacement decarbonization metrics.
 * DO NOT EXECUTE THIS FILE IN CI/CD OR LOCAL ENVIRONMENT AS PER TASK INSTRUCTIONS.
 */

const IndustrialHeatPumpEngine = require('../src/services/industrial_heat_pump_engine');
const { calculateHeatExchangerEfficiency, estimateThermalStorageTankSizeM3 } = require('../src/services/industrial_heat_pump_extension');
const INDUSTRIAL_REFRIGERANT_CATALOG = require('../src/services/industrial_refrigerant_catalog');

describe('IndustrialHeatPumpEngine Unit Test Suite', () => {
  let engine;

  beforeEach(() => {
    engine = new IndustrialHeatPumpEngine({
      facilityId: 'TEST-HTHP-01',
      wasteHeatSourceTempC: 45.0,
      requiredOutputTempC: 120.0,
      thermalLoadKw: 5000,
    });
  });

  test('should accurately calculate Carnot and realistic operating COP', () => {
    const cop = engine.calculateCoefficientOfPerformance();

    expect(cop.sourceTempC).toBe(45.0);
    expect(cop.sinkTempC).toBe(120.0);
    expect(cop.temperatureLiftC).toBe(75.0);
    expect(cop.carnotCop).toBeGreaterThan(4.5);
    expect(cop.operatingCop).toBeGreaterThan(2.0);
  });

  test('should throw error when source temperature is greater than or equal to sink temperature', () => {
    expect(() => {
      engine.calculateCoefficientOfPerformance(120.0, 45.0);
    }).toThrow();
  });

  test('should compute accurate electrical power input and absorbed waste heat', () => {
    const balance = engine.calculateEnergyBalance();

    expect(balance.requiredThermalOutputKw).toBe(5000);
    expect(balance.electricalPowerInputKw + balance.wasteHeatAbsorbedKw).toBeCloseTo(5000, -1);
  });

  test('should compute decarbonization offset comparing HTHP against legacy natural gas boiler', () => {
    const impact = engine.evaluateDecarbonizationImpact();

    expect(impact.legacyBoilerCo2TonnesYear).toBeGreaterThan(0);
    expect(impact.hthpElectrifiedCo2TonnesYear).toBeGreaterThan(0);
    expect(impact.netAnnualCo2OffsetTonnes).toBeDefined();
  });

  test('should validate refrigerant catalog and extension functions', () => {
    expect(INDUSTRIAL_REFRIGERANT_CATALOG.length).toBe(4);
    const eff = calculateHeatExchangerEfficiency(80, 50, 30);
    expect(eff).toBe(0.6);
    const tankM3 = estimateThermalStorageTankSizeM3(5000, 2);
    expect(tankM3).toBeGreaterThan(100);
  });
});
