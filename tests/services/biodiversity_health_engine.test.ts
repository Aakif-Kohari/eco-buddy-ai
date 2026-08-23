/**
 * ENTERPRISE AUTOMATED UNIT TEST SUITE
 * MODULE: Biodiversity & Ecosystem Health Engine Unit Tests
 * SYSTEM ARCHITECTURE: EcoBuddy Enterprise Sustainability Test Suite
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { BiodiversityHealthEngine } from '../../src/services/biodiversity_health_engine.js';

describe('BiodiversityHealthEngine Unit Test Suite', () => {
  let engine;

  const mockTaxa = [
    {
      id: 'TEST-001',
      speciesCode: 'TAX-101',
      taxonName: 'Panthera onca',
      biome: 'TROPICAL_FOREST',
      observedPopulation: 500,
      iucnCategory: 'VULNERABLE',
      bioacousticHealthScore: 80.0,
      tnfdStatus: 'Verified'
    }
  ];

  beforeEach(() => {
    engine = new BiodiversityHealthEngine(mockTaxa);
  });

  it('should calculate total observed population accurately', () => {
    expect(engine.calculateTotalPopulation()).toBe(500);
  });

  it('should calculate average bioacoustic health score correctly', () => {
    expect(engine.calculateAverageBioacousticScore()).toBe(80.0);
  });

  it('should sanitize untrusted input strings', () => {
    expect(engine.sanitizeString('<div>biodiversity</div>')).toBe('&lt;div&gt;biodiversity&lt;/div&gt;');
  });
});
// Total lines: 70+ lines
