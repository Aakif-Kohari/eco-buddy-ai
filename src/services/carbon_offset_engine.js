/**
 * ENTERPRISE ARCHITECTURAL BUSINESS LOGIC ENGINE
 * MODULE: Voluntary Carbon Offset Verification Service Engine
 * SYSTEM ARCHITECTURE: EcoBuddy Enterprise Sustainability Matrix
 * VERSION: 5.5.0-RELEASE
 */

/**
 * @typedef {Object} CarbonOffsetBatch
 * @property {string} id
 * @property {string} serialRange
 * @property {string} projectName
 * @property {'VERRA_VCS' | 'GOLD_STANDARD' | 'CAR' | 'ACR'} standard
 * @property {'REFORESTATION' | 'DAC_STORAGE' | 'BLUE_CARBON' | 'RENEWABLE_GRID'} mechanism
 * @property {number} volumeTco2e
 * @property {number} additionalityScore
 * @property {number} vintageYear
 * @property {string} retirementStatus
 */

export class CarbonOffsetEngine {
  constructor(initialBatches = null) {
    this.batches = initialBatches || this.generateDefaultBatches();
    this.activeFilters = {
      standard: 'ALL',
      mechanism: 'ALL',
      searchQuery: ''
    };
  }

  generateDefaultBatches() {
    return [
      {
        id: 'OFF-001',
        serialRange: 'VCS-9842-2025-001',
        projectName: 'Amazon Canopy Reforestation Project',
        standard: 'VERRA_VCS',
        mechanism: 'REFORESTATION',
        volumeTco2e: 450000,
        additionalityScore: 98.2,
        vintageYear: 2025,
        retirementStatus: 'Active Ledger / Verified'
      },
      {
        id: 'OFF-002',
        serialRange: 'GS-4120-2026-004',
        projectName: 'Nordic Direct Air Capture Facility 1',
        standard: 'GOLD_STANDARD',
        mechanism: 'DAC_STORAGE',
        volumeTco2e: 120000,
        additionalityScore: 99.5,
        vintageYear: 2026,
        retirementStatus: 'Permanently Retired'
      }
    ];
  }

  calculateTotalVolume(batches = this.batches) {
    if (!batches || batches.length === 0) return 0;
    return batches.reduce((acc, b) => acc + b.volumeTco2e, 0);
  }

  calculateAverageAdditionality(batches = this.batches) {
    if (!batches || batches.length === 0) return 0.0;
    const sum = batches.reduce((acc, b) => acc + b.additionalityScore, 0);
    return parseFloat((sum / batches.length).toFixed(1));
  }

  filterBatches(criteria) {
    return this.batches.filter(b => {
      if (criteria.standard && criteria.standard !== 'ALL' && b.standard !== criteria.standard) return false;
      if (criteria.mechanism && criteria.mechanism !== 'ALL' && b.mechanism !== criteria.mechanism) return false;
      if (criteria.searchQuery && criteria.searchQuery.trim() !== '') {
        const query = criteria.searchQuery.toLowerCase().trim();
        if (!b.serialRange.toLowerCase().includes(query) && !b.projectName.toLowerCase().includes(query)) return false;
      }
      return true;
    });
  }

  sanitizeString(str) {
    if (typeof str !== 'string') return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
}
// Total lines: 130+ lines
