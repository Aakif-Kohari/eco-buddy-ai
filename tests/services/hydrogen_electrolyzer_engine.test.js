/**
 * Enterprise Architectural Specification & Header:
 * Module: Automated Unit Test Suite for Green Hydrogen Production & Electrolyzer Analytics Engine
 * File: tests/services/hydrogen_electrolyzer_engine.test.js
 * Framework: Jest JS / Enterprise Decarbonization Telemetry Test Suite
 * Coverage Goal: 100% Statement & Branch Coverage Compliance
 *
 * Test Scenarios:
 * 1. Constructor Initialization & Default Configuration Fallbacks
 * 2. Faraday's Law Hydrogen Mass Production Yield Calculation
 * 3. Specific Energy Consumption (SEC) & LHV/HHV Thermal Efficiency Validation
 * 4. Levelized Cost of Hydrogen (LCOH) & Carbon Abatement Simulation
 * 5. Input Sanitation Security Review against XSS Injections
 */

const HydrogenElectrolyzerEngine = require('../../src/services/hydrogen_electrolyzer_engine');

describe('HydrogenElectrolyzerEngine Enterprise Core Suite', () => {
  let engine;

  beforeEach(() => {
    engine = new HydrogenElectrolyzerEngine({
      plantId: 'PLANT-TEST-88',
      nominalPowerMw: 50.0,
      faradaicEfficiency: 0.99
    });
  });

  describe('Constructor & State Initialization', () => {
    test('should initialize with custom plant configuration parameters', () => {
      expect(engine.plantState.plantId).toBe('PLANT-TEST-88');
      expect(engine.plantState.nominalPowerMw).toBe(50.0);
      expect(engine.plantState.faradaicEfficiency).toBe(0.99);
    });

    test('should initialize default stack telemetry stream cache', () => {
      const stack1 = engine.telemetryCache.get('STACK-01');
      expect(stack1).toBeDefined();
      expect(stack1.tech).toBe('PEM');
      expect(stack1.status).toBe('OPERATIONAL');
    });
  });

  describe('Faraday Hydrogen Production Yield Analytics', () => {
    test('should compute accurate hydrogen mass yield in kg/h for given stack current', () => {
      const currentAmps = 3500; // 3.5 kA stack current
      const yieldKgH = engine.calculateFaradayHydrogenYield(currentAmps, 120, 0.985);
      expect(yieldKgH).toBeGreaterThan(10.0);
      expect(yieldKgH).toBeLessThan(20.0);
      expect(typeof yieldKgH).toBe('number');
    });

    test('should throw error for negative stack operating current', () => {
      expect(() => engine.calculateFaradayHydrogenYield(-100)).toThrow(
        'Current must be a non-negative number.'
      );
    });
  });

  describe('Specific Power Consumption (SEC) & Thermal Efficiency', () => {
    test('should calculate valid SEC (kWh/kg) and LHV stack efficiency', () => {
      const secMetrics = engine.calculateSpecificEnergyConsumption(100.0, 1950.0);
      expect(secMetrics.secKwhPerKg).toBeGreaterThan(45.0);
      expect(secMetrics.secKwhPerKg).toBeLessThan(60.0);
      expect(secMetrics.lhvEfficiencyPct).toBeGreaterThan(50.0);
      expect(secMetrics.lhvEfficiencyPct).toBeLessThan(80.0);
    });

    test('should throw error when hydrogen yield is zero or negative', () => {
      expect(() => engine.calculateSpecificEnergyConsumption(100.0, 0)).toThrow(
        'Hydrogen yield must be strictly greater than 0 kg/h.'
      );
      expect(() => engine.calculateSpecificEnergyConsumption(100.0, -10)).toThrow(
        'Hydrogen yield must be strictly greater than 0 kg/h.'
      );
    });
  });

  describe('LCOH & Carbon Abatement Financial Simulation', () => {
    test('should accurately compute LCOH ($/kg) and annual decarbonization metric', () => {
      const sim = engine.simulateLcohAndAbatement({
        powerInputMw: 100.0,
        electricityCostPerMwh: 40.0,
        stackEfficiencyLhvPct: 67.0
      });

      expect(sim.hourlyH2YieldKg).toBeGreaterThan(1500);
      expect(sim.lcohDollarsPerKg).toBeGreaterThan(1.50);
      expect(sim.lcohDollarsPerKg).toBeLessThan(6.00);
      expect(sim.annualCo2AbatedTonnes).toBeGreaterThan(100000);
    });
  });

  describe('Input Sanitation Security Validation', () => {
    test('should sanitize malicious HTML and script tags', () => {
      const scriptMalware = '<img src=x onerror=alert(1)>';
      const clean = engine.sanitizeInput(scriptMalware);
      expect(clean).not.toContain('<img');
      expect(clean).toContain('&lt;img');
    });

    test('should handle non-string arguments gracefully', () => {
      expect(engine.sanitizeInput(undefined)).toBe('');
      expect(engine.sanitizeInput({ key: 'val' })).toBe('');
    });
  });
});
