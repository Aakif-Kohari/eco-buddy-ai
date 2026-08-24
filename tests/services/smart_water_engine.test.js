/**
 * Enterprise Architectural Specification & Header:
 * Module: Automated Unit Test Suite for Smart Water Management & RO Desalination Engine
 * File: tests/services/smart_water_engine.test.js
 * Framework: Jest JS / Enterprise Hydrological Telemetry Test Suite
 * Coverage Goal: 100% Statement & Branch Coverage Compliance
 *
 * Test Scenarios:
 * 1. Constructor Initialization & Default Configuration Fallbacks
 * 2. Osmotic Pressure Calculation via Van 't Hoff Equation
 * 3. Reverse Osmosis Specific Energy Consumption (SEC) & ERD Efficiency Model
 * 4. Membrane Fouling & CIP Urgency Metric Generation
 * 5. Mass Balance & Carbon Footprint Offset Simulation
 * 6. Input Sanitation against Cross-Site Scripting (XSS) Attacks
 */

const SmartWaterEngine = require('../../src/services/smart_water_engine');

describe('SmartWaterEngine Enterprise Core Suite', () => {
  let engine;

  beforeEach(() => {
    engine = new SmartWaterEngine({
      facilityId: 'FAC-TEST-99',
      rawIntakeFlow: 250000,
      recoveryTarget: 0.50
    });
  });

  describe('Constructor & State Initialization', () => {
    test('should initialize with custom configuration parameters', () => {
      expect(engine.facilityState.facilityId).toBe('FAC-TEST-99');
      expect(engine.facilityState.rawIntakeFlow).toBe(250000);
      expect(engine.facilityState.recoveryTarget).toBe(0.50);
    });

    test('should initialize default mock telemetry trains', () => {
      const trainA = engine.telemetryCache.get('TRAIN-ALPHA');
      expect(trainA).toBeDefined();
      expect(trainA.feedPressureBar).toBe(64.5);
      expect(trainA.status).toBe('OPERATIONAL');
    });
  });

  describe('Thermodynamic Osmotic Pressure Calculation', () => {
    test('should calculate accurate osmotic pressure for standard seawater TDS (35,400 ppm)', () => {
      const osmoticPressure = engine.calculateOsmoticPressure(35400, 25);
      expect(osmoticPressure).toBeGreaterThan(25.0);
      expect(osmoticPressure).toBeLessThan(30.0);
      expect(typeof osmoticPressure).toBe('number');
    });

    test('should throw an error for negative or invalid TDS values', () => {
      expect(() => engine.calculateOsmoticPressure(-500)).toThrow(
        'Invalid TDS concentration: Must be a non-negative number.'
      );
      expect(() => engine.calculateOsmoticPressure('invalid')).toThrow(
        'Invalid TDS concentration: Must be a non-negative number.'
      );
    });
  });

  describe('Specific Energy Consumption (SEC) Analytics', () => {
    test('should compute valid SEC in kWh/m³ for high-efficiency isobaric ERD setup', () => {
      const sec = engine.calculateSpecificEnergyConsumption(64.5, 0.485, 0.972, 0.88);
      expect(sec).toBeGreaterThan(2.0);
      expect(sec).toBeLessThan(4.5);
    });

    test('should throw error when recovery rate is out of valid bounds (<= 0 or >= 1)', () => {
      expect(() => engine.calculateSpecificEnergyConsumption(60.0, 0.0, 0.95, 0.85)).toThrow(
        'Recovery rate must be a fraction strictly between 0 and 1.'
      );
      expect(() => engine.calculateSpecificEnergyConsumption(60.0, 1.2, 0.95, 0.85)).toThrow(
        'Recovery rate must be a fraction strictly between 0 and 1.'
      );
    });
  });

  describe('Membrane Fouling & CIP Urgency Prediction', () => {
    test('should return LOW urgency for optimal SDI and ΔP parameters', () => {
      const assessment = engine.predictMembraneFouling(1.5, 1.1, 1000);
      expect(assessment.cipUrgency).toBe('LOW');
      expect(assessment.riskScore).toBeLessThan(45);
    });

    test('should return CRITICAL urgency when SDI and ΔP exceed operating thresholds', () => {
      const assessment = engine.predictMembraneFouling(4.5, 2.8, 4000);
      expect(assessment.cipUrgency).toBe('CRITICAL');
      expect(assessment.recommendedAction).toContain('CIP Clean Immediately');
    });

    test('should return MEDIUM urgency for moderate fouling parameters', () => {
      const assessment = engine.predictMembraneFouling(3.2, 1.6, 2500);
      expect(assessment.cipUrgency).toBe('MEDIUM');
    });
  });

  describe('Mass Balance & Decarbonization Simulation', () => {
    test('should accurately simulate closed-loop mass balance metrics', () => {
      const simulation = engine.simulateMassBalance({
        rawIntakeFlow: 300000,
        targetRecoveryPct: 50.0,
        erdEfficiencyPct: 97.0,
        recycledBlendRatioPct: 20.0
      });

      expect(simulation.netPermeateFlowM3).toBeGreaterThan(150000);
      expect(simulation.brineDischargeFlowM3).toBeGreaterThan(0);
      expect(simulation.dailyCo2OffsetTonnes).toBeGreaterThan(0);
      expect(simulation.sustainabilityGrade).toBe('A+');
    });
  });

  describe('Input Sanitation Security Review', () => {
    test('should sanitize malicious script tags and HTML entities', () => {
      const maliciousInput = '<script>alert("XSS Attack")</script>';
      const cleanInput = engine.sanitizeInput(maliciousInput);
      expect(cleanInput).not.toContain('<script>');
      expect(cleanInput).toContain('&lt;script&gt;');
    });

    test('should handle non-string input safely', () => {
      expect(engine.sanitizeInput(null)).toBe('');
      expect(engine.sanitizeInput(12345)).toBe('');
    });
  });
});
