/**
 * Unit & Integration Test Suite for Waste Heat Thermoelectric Generator Engine
 * Tests Seebeck voltage generation, maximum power transfer, and conversion efficiency.
 * DO NOT EXECUTE THIS FILE IN CI/CD OR LOCAL ENVIRONMENT AS PER TASK INSTRUCTIONS.
 */

const WasteHeatTegEngine = require('../src/services/waste_heat_teg_engine');
const { calculateArrayPowerOutput, calculateAnnualCo2SavingsFromHarvest } = require('../src/services/waste_heat_teg_extension');
const THERMOELECTRIC_MATERIALS_CATALOG = require('../src/services/thermoelectric_materials_catalog');

describe('WasteHeatTegEngine Unit Test Suite', () => {
  let engine;

  beforeEach(() => {
    engine = new WasteHeatTegEngine({
      facilityId: 'TEST-TEG-01',
      hotSideExhaustTempC: 350.0,
      coldSideCoolantTempC: 40.0,
    });
  });

  test('should accurately calculate Seebeck open-circuit voltage for given temperature delta', () => {
    const voltage = engine.calculateSeebeckVoltage();

    expect(voltage.hotSideTempC).toBe(350.0);
    expect(voltage.coldSideTempC).toBe(40.0);
    expect(voltage.tempDeltaC).toBe(310.0);
    expect(voltage.openCircuitVoltageVolts).toBeGreaterThan(60.0);
  });

  test('should throw error when hot side temperature is not strictly greater than cold side', () => {
    expect(() => {
      engine.calculateSeebeckVoltage(40.0, 350.0);
    }).toThrow();
  });

  test('should compute maximum power transfer and operating current under matched load', () => {
    const power = engine.calculatePowerOutput();

    expect(power.maxElectricalPowerWatts).toBeGreaterThan(350);
    expect(power.operatingVoltageVolts).toBeCloseTo(power.openCircuitVoltageVolts / 2, 1);
  });

  test('should compute Carnot limit and net thermal-to-electric conversion efficiency', () => {
    const eff = engine.evaluateConversionEfficiency();

    expect(eff.dimensionlessZt).toBe(1.1);
    expect(eff.carnotLimitPct).toBeGreaterThan(45.0);
    expect(eff.netThermalToElectricEfficiencyPct).toBeGreaterThan(5.0);
    expect(eff.dailyEnergyHarvestedKwh).toBeGreaterThan(5.0);
  });

  test('should validate materials catalog and array extension functions', () => {
    expect(THERMOELECTRIC_MATERIALS_CATALOG.length).toBe(4);
    const array = calculateArrayPowerOutput(400, 10);
    expect(array.totalArrayPowerKw).toBe(4.0);
    const co2 = calculateAnnualCo2SavingsFromHarvest(10, 0.45);
    expect(co2.annualCo2OffsetTonnes).toBe(1.64);
  });
});
