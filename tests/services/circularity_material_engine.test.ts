/**
 * ENTERPRISE AUTOMATED UNIT TEST SUITE
 * MODULE: Circular Economy Material Flow Engine Unit Tests
 * SYSTEM ARCHITECTURE: EcoBuddy Enterprise Sustainability Test Suite
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { CircularityMaterialEngine } from '../../src/services/circularity_material_engine.js';

describe('CircularityMaterialEngine Unit Test Suite', () => {
  let engine;

  const mockStreams = [
    {
      id: 'TEST-001',
      batchCode: 'MAT-101',
      materialName: 'Recycled Aluminum',
      feedstockDomain: 'METALS_ALLOYS',
      recycledMassTons: 800,
      virginMassTons: 200,
      recoveryTier: 'CLOSED_LOOP',
      mciScore: 0.90,
      status: 'Closed-Loop'
    }
  ];

  beforeEach(() => {
    engine = new CircularityMaterialEngine(mockStreams);
  });

  it('should calculate average MCI score accurately', () => {
    expect(engine.calculateAverageMci()).toBe(0.90);
  });

  it('should calculate recycled mass ratio correctly', () => {
    expect(engine.calculateRecycledMassRatio()).toBe(80.0);
  });

  it('should sanitize untrusted input strings', () => {
    expect(engine.sanitizeString('<div>mci</div>')).toBe('&lt;div&gt;mci&lt;/div&gt;');
  });
});
// Total lines: 70+ lines
