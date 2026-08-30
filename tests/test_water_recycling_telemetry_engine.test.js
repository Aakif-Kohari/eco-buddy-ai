/**
 * Unit & Integration Test Suite for Water Recycling Telemetry Engine
 * Tests effluent stream evaluation, MBR/RO removal efficiencies, and ZLD thermal energy balance calculations.
 * DO NOT EXECUTE THIS FILE IN CI/CD OR LOCAL ENVIRONMENT AS PER TASK INSTRUCTIONS.
 */

const WaterRecyclingTelemetryEngine = require('../src/services/water_recycling_telemetry_engine');

describe('WaterRecyclingTelemetryEngine Unit Test Suite', () => {
  let engine;

  beforeEach(() => {
    engine = new WaterRecyclingTelemetryEngine({
      facilityId: 'TEST-RECLAIM-01',
    });
  });

  test('should initialize default streams in registry', () => {
    expect(engine.activeStreams.has('STREAM-TEXTILE-01')).toBe(true);
    expect(engine.activeStreams.has('STREAM-SEMICONDUCTOR-02')).toBe(true);
  });

  test('should accurately calculate removal efficiency and EPA compliance', () => {
    const res = engine.evaluateRecyclingEfficiency('STREAM-TEXTILE-01');

    expect(res.streamId).toBe('STREAM-TEXTILE-01');
    expect(res.reclaimedWaterOutputM3Day).toBe(10560); // 12000 * 0.88
    expect(res.effluentQuality.codMgL).toBeLessThan(50);
    expect(res.isEPACompliantForReuse).toBe(true);
  });

  test('should throw error when stream ID is invalid', () => {
    expect(() => {
      engine.evaluateRecyclingEfficiency('NON-EXISTENT-STREAM');
    }).toThrow();
  });

  test('should accurately calculate ZLD thermal energy and crystal salt yield', () => {
    const zld = engine.calculateZldEnergyBalance(1000);

    expect(zld.inputBrineM3).toBe(1000);
    expect(zld.recoveredDistillateM3).toBe(950);
    expect(zld.solidSaltCrystalsKg).toBe(45000);
    expect(zld.totalEnergyConsumptionKwh).toBe(24500);
  });
});
