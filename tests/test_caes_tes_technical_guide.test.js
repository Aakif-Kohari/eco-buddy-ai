/**
 * Additional Unit Tests for CAES TES Technical Guide
 */

const CAES_TES_TECHNICAL_GUIDE = require('../src/services/caes_tes_technical_guide');

describe('CAES TES Technical Guide Test Suite', () => {
  test('should load TES technical components correctly', () => {
    expect(CAES_TES_TECHNICAL_GUIDE.length).toBe(3);
    expect(CAES_TES_TECHNICAL_GUIDE[0].component).toContain('Thermal Energy Storage');
  });
});
