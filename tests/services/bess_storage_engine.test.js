/**
 * Enterprise Architectural Specification & Header:
 * Module: Automated Unit Test Suite for Smart Grid BESS Battery Storage Engine
 * File: tests/services/bess_storage_engine.test.js
 * Framework: Jest JS / Enterprise Grid Telemetry Test Suite
 * Coverage Goal: 100% Statement & Branch Coverage Compliance
 *
 * Test Scenarios:
 * 1. Constructor Initialization & Default Configuration Fallbacks
 * 2. Round-Trip Efficiency (RTE) Calculation taking PCS losses into account
 * 3. State of Health (SoH) Capacity Fade Prediction
 * 4. Grid Arbitrage Financial Dispatch Simulation
 * 5. Input Sanitation Security Review against Cross-Site Scripting (XSS)
 */

const BessStorageEngine = require('../../src/services/bess_storage_engine');

describe('BessStorageEngine Enterprise Core Suite', () => {
  let engine;

  beforeEach(() => {
    engine = new BessStorageEngine({
      facilityId: 'BESS-TEST-77',
      installedEnergyMwh: 200.0,
      powerRatingMw: 50.0
    });
  });

  describe('Constructor & State Initialization', () => {
    test('should initialize with custom BESS facility parameters', () => {
      expect(engine.facilityState.facilityId).toBe('BESS-TEST-77');
      expect(engine.facilityState.installedEnergyMwh).toBe(200.0);
      expect(engine.facilityState.powerRatingMw).toBe(50.0);
    });

    test('should initialize default mock container telemetry streams', () => {
      const container1 = engine.telemetryCache.get('CONTAINER-01');
      expect(container1).toBeDefined();
      expect(container1.chem).toBe('LFP');
      expect(container1.status).toBe('OPERATIONAL');
    });
  });

  describe('Round-Trip Efficiency (RTE) Analytics', () => {
    test('should compute accurate RTE % for standard PCS and battery cell parameters', () => {
      const rte = engine.calculateRoundTripEfficiency(0.965, 0.992);
      expect(rte).toBeGreaterThan(85.0);
      expect(rte).toBeLessThan(95.0);
      expect(typeof rte).toBe('number');
    });

    test('should throw error for out-of-bounds efficiency input parameters', () => {
      expect(() => engine.calculateRoundTripEfficiency(-0.5, 0.99)).toThrow(
        'Efficiency parameters must be fractions between 0 and 1.0.'
      );
      expect(() => engine.calculateRoundTripEfficiency(1.2, 0.99)).toThrow(
        'Efficiency parameters must be fractions between 0 and 1.0.'
      );
    });
  });

  describe('State-of-Health (SoH) Capacity Fade Prediction', () => {
    test('should return EXCELLENT health status for low cycle count', () => {
      const fadeMetrics = engine.predictCapacityFade(500, 12);
      expect(fadeMetrics.healthStatus).toBe('EXCELLENT');
      expect(fadeMetrics.sohPct).toBeGreaterThan(90.0);
      expect(fadeMetrics.remainingCyclesToEol).toBeGreaterThan(3000);
    });

    test('should throw error for negative cycle count or age months', () => {
      expect(() => engine.predictCapacityFade(-10, 12)).toThrow(
        'Cycle count and age months must be non-negative values.'
      );
      expect(() => engine.predictCapacityFade(100, -5)).toThrow(
        'Cycle count and age months must be non-negative values.'
      );
    });
  });

  describe('Grid Arbitrage Financial Simulation', () => {
    test('should calculate valid daily arbitrage revenue and ROI', () => {
      const sim = engine.simulateGridArbitrage({
        storageCapacityMwh: 500,
        powerRatingMw: 125,
        offpeakPricePerMwh: 20.0,
        peakPricePerMwh: 150.0
      });

      expect(sim.dispatchedEnergyMwh).toBeGreaterThan(300);
      expect(sim.energyLossesMwh).toBeGreaterThan(0);
      expect(sim.netDailyRevenueDollars).toBeGreaterThan(10000);
      expect(sim.annualizedRoiPct).toBeGreaterThan(5.0);
    });
  });

  describe('Input Sanitation Security Validation', () => {
    test('should sanitize malicious script tags and HTML entities', () => {
      const malicious = '<script>document.cookie=""</script>';
      const clean = engine.sanitizeInput(malicious);
      expect(clean).not.toContain('<script>');
      expect(clean).toContain('&lt;script&gt;');
    });

    test('should handle non-string arguments safely', () => {
      expect(engine.sanitizeInput(null)).toBe('');
      expect(engine.sanitizeInput(9999)).toBe('');
    });
  });
});
