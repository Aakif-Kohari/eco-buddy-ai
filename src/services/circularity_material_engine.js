/**
 * ENTERPRISE ARCHITECTURAL BUSINESS LOGIC ENGINE
 * MODULE: Circular Economy Material Flow Service Engine
 * SYSTEM ARCHITECTURE: EcoBuddy Enterprise Sustainability Matrix
 * VERSION: 5.3.0-RELEASE
 */

/**
 * @typedef {Object} MaterialStream
 * @property {string} id
 * @property {string} batchCode
 * @property {string} materialName
 * @property {'METALS_ALLOYS' | 'BIO_POLYMERS' | 'GLASS_CERAMICS' | 'RARE_EARTH'} feedstockDomain
 * @property {number} recycledMassTons
 * @property {number} virginMassTons
 * @property {'CLOSED_LOOP' | 'OPEN_LOOP' | 'DOWN_CYCLING'} recoveryTier
 * @property {number} mciScore
 * @property {string} status
 */

export class CircularityMaterialEngine {
  constructor(initialStreams = null) {
    this.streams = initialStreams || this.generateDefaultStreams();
    this.activeFilters = {
      domain: 'ALL',
      recoveryTier: 'ALL',
      searchQuery: ''
    };
  }

  generateDefaultStreams() {
    return [
      {
        id: 'STRM-001',
        batchCode: 'MAT-ALU-901',
        materialName: 'Automotive Aircraft Grade Recycled Aluminum',
        feedstockDomain: 'METALS_ALLOYS',
        recycledMassTons: 850,
        virginMassTons: 150,
        recoveryTier: 'CLOSED_LOOP',
        mciScore: 0.94,
        status: 'Closed-Loop Remanufactured'
      },
      {
        id: 'STRM-002',
        batchCode: 'MAT-BIO-402',
        materialName: 'Ocean-Bound Bio-Plastic Resin',
        feedstockDomain: 'BIO_POLYMERS',
        recycledMassTons: 620,
        virginMassTons: 380,
        recoveryTier: 'OPEN_LOOP',
        mciScore: 0.78,
        status: 'Upcycled to Consumer Goods'
      }
    ];
  }

  calculateAverageMci(streams = this.streams) {
    if (!streams || streams.length === 0) return 0.0;
    const sum = streams.reduce((acc, s) => acc + s.mciScore, 0);
    return parseFloat((sum / streams.length).toFixed(2));
  }

  calculateRecycledMassRatio(streams = this.streams) {
    if (!streams || streams.length === 0) return 0.0;
    const totalRecycled = streams.reduce((acc, s) => acc + s.recycledMassTons, 0);
    const totalVirgin = streams.reduce((acc, s) => acc + s.virginMassTons, 0);
    const totalMass = totalRecycled + totalVirgin;
    if (totalMass === 0) return 0.0;
    return parseFloat(((totalRecycled / totalMass) * 100).toFixed(1));
  }

  filterStreams(criteria) {
    return this.streams.filter(s => {
      if (criteria.domain && criteria.domain !== 'ALL' && s.feedstockDomain !== criteria.domain) return false;
      if (criteria.recoveryTier && criteria.recoveryTier !== 'ALL' && s.recoveryTier !== criteria.recoveryTier) return false;
      if (criteria.searchQuery && criteria.searchQuery.trim() !== '') {
        const query = criteria.searchQuery.toLowerCase().trim();
        if (!s.batchCode.toLowerCase().includes(query) && !s.materialName.toLowerCase().includes(query)) return false;
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
