/**
 * Enterprise Architectural Specification & Header:
 * Module: Automated Unit Test Suite for Direct Air Capture (DAC) & Carbon Removal Engine
 * File: tests/services/dac_removal_engine.test.js
 * Framework: Jest JS / Enterprise CDR Telemetry Test Suite
 * Coverage Goal: 100% Statement & Branch Coverage Compliance
 *
 * Test Scenarios:
 * 1. Constructor Initialization & Default Configuration Fallbacks
 * 2. Specific Thermal Energy Consumption Calculation (GJ/tCO2)
 * 3. Parasitic Emissions & Net Carbon Removal Efficiency Analytics
 * 4. Net CDR Simulation & Puro.earth CORCs Credit Issuance
 * 5. Input Sanitation Security Review against Cross-Site Scripting (XSS)
 */

const DacRemovalEngine = require('../../src/services/dac_removal_engine');

describe('DacRemovalEngine Enterprise Core Suite', () => {
  let engine;

  beforeEach(() => {
    engine = new DacRemovalEngine({
      plantId: 'DAC-TEST-100',
      grossDailyTargetTonnes: 500.0,
      heatSource: 'GEOTHERMAL'
    });
  });

  describe('Constructor & State Initialization', () => {
    test('should initialize with custom plant configuration parameters', () => {
      expect(engine.plantState.plantId).toBe('DAC-TEST-100');
      expect(engine.plantState.grossDailyTargetTonnes).toBe(500.0);
      expect(engine.plantState.heatSource).toBe('GEOTHERMAL');
    });

    test('should initialize default mock collector telemetry streams', () => {
      const block1 = engine.telemetryCache.get('BLOCK-01');
      expect(block1).toBeDefined();
      expect(block1.mode).toBe('ADSORPTION');
      expect(block1.status).toBe('OPERATIONAL');
    });
  });

  describe('Specific Thermal Energy Consumption Analytics', () => {
    test('should calculate valid thermal energy (GJ/tCO2) for given heat input and captured mass', () => {
      const thermalGjPerTonne = engine.calculateSpecificThermalEnergy(5500.0, 1000.0);
      expect(thermalGjPerTonne).toBeCloseTo(5.5, 2);
      expect(typeof thermalGjPerTonne).toBe('number');
    });

    test('should throw error for zero or negative gross captured CO2 mass', () => {
      expect(() => engine.calculateSpecificThermalEnergy(5000.0, 0)).toThrow(
        'Gross CO2 captured must be strictly greater than 0 tonnes.'
      );
    });
  });

  describe('Parasitic Emissions & Net CDR Efficiency', () => {
    test('should compute high net efficiency (>90%) for Geothermal heat source', () => {
      const cdrMetrics = engine.calculateNetCdrEfficiency(1000.0, 5.5, 'GEOTHERMAL');
      expect(cdrMetrics.netEfficiencyPct).toBeGreaterThan(90.0);
      expect(cdrMetrics.parasiticLossTonnes).toBeLessThan(100.0);
      expect(cdrMetrics.netCdrTonnes).toBeGreaterThan(900.0);
    });

    test('should account for higher parasitic emissions with Heat Pump energy source', () => {
      const geothermalNet = engine.calculateNetCdrEfficiency(1000.0, 5.5, 'GEOTHERMAL');
      const heatPumpNet = engine.calculateNetCdrEfficiency(1000.0, 5.5, 'HEAT_PUMP');
      expect(heatPumpNet.netEfficiencyPct).toBeLessThan(geothermalNet.netEfficiencyPct);
    });

    test('should throw error for non-positive gross CO2 mass', () => {
      expect(() => engine.calculateNetCdrEfficiency(-100)).toThrow(
        'Gross CO2 mass must be positive.'
      );
    });
  });

  describe('Net CDR & Puro.earth CORCs Simulation', () => {
    test('should accurately calculate annual CORCs issued based on net daily CDR', () => {
      const sim = engine.simulateNetCdrAndCorcs({
        grossCaptureTonnes: 1000.0,
        thermalReqGjPerTonne: 5.0,
        heatSource: 'GEOTHERMAL'
      });

      expect(sim.netDailyCdrTonnes).toBeGreaterThan(900.0);
      expect(sim.annualCorcsIssued).toBeGreaterThan(300000);
    });
  });

  describe('Input Sanitation Security Validation', () => {
    test('should sanitize malicious script tags and HTML entities', () => {
      const malicious = '<iframe src="javascript:alert(1)"></iframe>';
      const clean = engine.sanitizeInput(malicious);
      expect(clean).not.toContain('<iframe');
      expect(clean).toContain('&lt;iframe');
    });

    test('should handle non-string inputs safely', () => {
      expect(engine.sanitizeInput(undefined)).toBe('');
      expect(engine.sanitizeInput(42)).toBe('');
    });
  });
});
