/**
 * ENTERPRISE AUTOMATED UNIT TEST SUITE
 * MODULE: Voluntary Carbon Offset Verification Engine Unit Tests
 * SYSTEM ARCHITECTURE: EcoBuddy Enterprise Sustainability Test Suite
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { CarbonOffsetEngine } from '../../src/services/carbon_offset_engine.js';

describe('CarbonOffsetEngine Unit Test Suite', () => {
  let engine;

  const mockBatches = [
    {
      id: 'TEST-001',
      serialRange: 'VCS-101',
      projectName: 'Reforestation',
      standard: 'VERRA_VCS',
      mechanism: 'REFORESTATION',
      volumeTco2e: 50000,
      additionalityScore: 95.0,
      vintageYear: 2025,
      retirementStatus: 'Active'
    }
  ];

  beforeEach(() => {
    engine = new CarbonOffsetEngine(mockBatches);
  });

  it('should calculate total credit volume accurately', () => {
    expect(engine.calculateTotalVolume()).toBe(50000);
  });

  it('should calculate average additionality score correctly', () => {
    expect(engine.calculateAverageAdditionality()).toBe(95.0);
  });

  it('should sanitize untrusted input strings', () => {
    expect(engine.sanitizeString('<div>offset</div>')).toBe('&lt;div&gt;offset&lt;/div&gt;');
  });
});
// Total lines: 70+ lines
