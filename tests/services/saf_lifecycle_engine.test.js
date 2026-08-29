/**
 * Enterprise Architectural Specification & Header:
 * Module: Automated Unit Test Suite for Sustainable Aviation Fuel (SAF) Lifecycle Engine
 * File: tests/services/saf_lifecycle_engine.test.js
 * Framework: Jest JS / Enterprise Aviation Decarbonization Test Suite
 * Coverage Goal: 100% Statement & Branch Coverage Compliance
 *
 * Test Scenarios:
 * 1. Constructor Initialization & Default Configuration Fallbacks
 * 2. Carbon Intensity (CI) Calculation across HEFA, PtL, and AtJ Feedstocks
 * 3. Percentage GHG Reduction Calculation vs Jet-A1 Baseline
 * 4. ICAO CORSIA Lifecycle Abatement & Annual CO2 Reduction Simulation
 * 5. Input Sanitation Security Review against Cross-Site Scripting (XSS)
 */

const SafLifecycleEngine = require('../../src/services/saf_lifecycle_engine');

describe('SafLifecycleEngine Enterprise Core Suite', () => {
  let engine;

  beforeEach(() => {
    engine = new SafLifecycleEngine({
      plantId: 'SAF-TEST-99',
      annualProductionTonnes: 250000,
      pathway: 'HEFA-UCO'
    });
  });

  describe('Constructor & State Initialization', () => {
    test('should initialize with custom plant configuration parameters', () => {
      expect(engine.plantState.plantId).toBe('SAF-TEST-99');
      expect(engine.plantState.annualProductionTonnes).toBe(250000);
      expect(engine.plantState.pathway).toBe('HEFA-UCO');
    });

    test('should initialize default mock reactor telemetry streams', () => {
      const stage1 = engine.telemetryCache.get('STAGE-01-HDO');
      expect(stage1).toBeDefined();
      expect(stage1.name).toBe('Hydrodeoxygenation');
      expect(stage1.status).toBe('OPERATIONAL');
    });
  });

  describe('Carbon Intensity (CI) Calculations', () => {
    test('should calculate valid CI for HEFA UCO with Green Hydrogen', () => {
      const ci = engine.calculateCarbonIntensity('UCO', 'GREEN');
      expect(ci).toBeGreaterThan(10.0);
      expect(ci).toBeLessThan(25.0);
      expect(typeof ci).toBe('number');
    });

    test('should apply hydrogen penalty for Grey Hydrogen refining', () => {
      const ciGreen = engine.calculateCarbonIntensity('UCO', 'GREEN');
      const ciGrey = engine.calculateCarbonIntensity('UCO', 'GREY');
      expect(ciGrey).toBeGreaterThan(ciGreen);
      expect(ciGrey - ciGreen).toBeCloseTo(14.8, 1);
    });
  });

  describe('GHG Reduction Percentage Analytics', () => {
    test('should compute accurate percentage reduction vs 89 gCO2e/MJ Jet-A1 baseline', () => {
      const reductionPct = engine.calculateGhgReductionPercentage(18.4);
      expect(reductionPct).toBeGreaterThan(75.0);
      expect(reductionPct).toBeLessThan(85.0);
    });

    test('should throw error for negative carbon intensity values', () => {
      expect(() => engine.calculateGhgReductionPercentage(-10.0)).toThrow(
        'Carbon Intensity cannot be negative.'
      );
    });
  });

  describe('ICAO CORSIA Lifecycle Simulation', () => {
    test('should calculate annual CO2 abatement and return CORSIA ELIGIBLE status', () => {
      const sim = engine.simulateCorsiaLifecycle({
        feedstockType: 'UCO',
        hydrogenSource: 'GREEN',
        annualVolumeTonnes: 500000,
        blendPercentage: 50.0
      });

      expect(sim.netCarbonIntensity).toBeLessThan(25.0);
      expect(sim.ghgReductionPct).toBeGreaterThan(70.0);
      expect(sim.annualCo2AbatedTonnes).toBeGreaterThan(1000000);
      expect(sim.corsiaEligible).toBe(true);
      expect(sim.corsiaStatus).toContain('PASSED');
    });
  });

  describe('Input Sanitation Security Validation', () => {
    test('should sanitize malicious script tags and HTML entities', () => {
      const malicious = '<script>window.location="http://attacker.com"</script>';
      const clean = engine.sanitizeInput(malicious);
      expect(clean).not.toContain('<script>');
      expect(clean).toContain('&lt;script&gt;');
    });

    test('should handle non-string inputs safely', () => {
      expect(engine.sanitizeInput(null)).toBe('');
      expect(engine.sanitizeInput(12345)).toBe('');
    });
  });
});
