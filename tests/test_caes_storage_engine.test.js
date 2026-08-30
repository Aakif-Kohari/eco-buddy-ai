/**
 * Unit & Integration Test Suite for CaesStorageEngine
 * Tests multi-stage compression power, cavern charging pressure dynamics, and round-trip efficiency.
 * DO NOT EXECUTE THIS FILE IN CI/CD OR LOCAL ENVIRONMENT AS PER TASK INSTRUCTIONS.
 */

const CaesStorageEngine = require('../src/services/caes_storage_engine');
const { calculateDischargeTurbinePower, calculateCavernAirMassTonnes } = require('../src/services/caes_storage_extension');
const CAES_CAVERN_CATALOG = require('../src/services/caes_cavern_catalog');

describe('CaesStorageEngine Unit Test Suite', () => {
  let engine;

  beforeEach(() => {
    engine = new CaesStorageEngine({
      facilityId: 'TEST-CAES-01',
      cavernVolumeM3: 300000,
      initialPressureBar: 50.0,
    });
  });

  test('should accurately calculate compression power and thermal heat capture rate', () => {
    const comp = engine.calculateCompressionPerformance(150.0, 75.0);

    expect(comp.airMassFlowKgSec).toBe(150.0);
    expect(comp.stagesCount).toBe(4);
    expect(comp.pressureRatioPerStage).toBeGreaterThan(2.5);
    expect(comp.compressorPowerMW).toBeGreaterThan(80.0);
    expect(comp.thermalHeatCapturedMW).toBeGreaterThan(30.0);
  });

  test('should throw error when air mass flow rate is invalid', () => {
    expect(() => {
      engine.calculateCompressionPerformance(-10);
    }).toThrow();
  });

  test('should simulate cavern pressure growth during charging cycle', () => {
    const charge = engine.simulateChargingCycle(6.0, 150.0);

    expect(charge.chargingHours).toBe(6.0);
    expect(charge.airAddedTonnes).toBe(3240);
    expect(charge.newCavernPressureBar).toBeGreaterThan(50.0);
  });

  test('should evaluate round-trip efficiency for adiabatic CAES system with TES', () => {
    const rte = engine.evaluateRoundTripEfficiency(0.88);

    expect(rte.roundTripEfficiencyPct).toBeGreaterThan(65.0);
    expect(rte.gridDecarbonizationGrade).toBe('A+');
  });

  test('should validate cavern catalog and extension functions', () => {
    expect(CAES_CAVERN_CATALOG.length).toBe(4);
    const turbine = calculateDischargeTurbinePower(150, 60, 550);
    expect(turbine.turbineOutputMW).toBeGreaterThan(50.0);
    const mass = calculateCavernAirMassTonnes(300000, 50, 40);
    expect(mass).toBeGreaterThan(15000);
  });
});
