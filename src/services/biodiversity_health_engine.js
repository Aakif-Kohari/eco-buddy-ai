/**
 * ENTERPRISE ARCHITECTURAL BUSINESS LOGIC ENGINE
 * MODULE: Biodiversity & Ecosystem Health Service Engine
 * SYSTEM ARCHITECTURE: EcoBuddy Enterprise Sustainability Matrix
 * VERSION: 5.4.0-RELEASE
 */

/**
 * @typedef {Object} SpeciesTaxon
 * @property {string} id
 * @property {string} speciesCode
 * @property {string} taxonName
 * @property {'TROPICAL_FOREST' | 'CORAL_REEF' | 'WETLANDS' | 'TEMPERATE_TAIGA'} biome
 * @property {number} observedPopulation
 * @property {'CRITICAL' | 'ENDANGERED' | 'VULNERABLE' | 'LEAST_CONCERN'} iucnCategory
 * @property {number} bioacousticHealthScore
 * @property {string} tnfdStatus
 */

export class BiodiversityHealthEngine {
  constructor(initialTaxa = null) {
    this.taxa = initialTaxa || this.generateDefaultTaxa();
    this.activeFilters = {
      biome: 'ALL',
      iucnCategory: 'ALL',
      searchQuery: ''
    };
  }

  generateDefaultTaxa() {
    return [
      {
        id: 'TAX-001',
        speciesCode: 'TAX-JAG-901',
        taxonName: 'Panthera onca (Amazonian Jaguar)',
        biome: 'TROPICAL_FOREST',
        observedPopulation: 420,
        iucnCategory: 'VULNERABLE',
        bioacousticHealthScore: 88.5,
        tnfdStatus: 'TNFD Nature-Positive Offset'
      },
      {
        id: 'TAX-002',
        speciesCode: 'TAX-COR-304',
        taxonName: 'Acropora cervicornis (Staghorn Coral)',
        biome: 'CORAL_REEF',
        observedPopulation: 12500,
        iucnCategory: 'CRITICAL',
        bioacousticHealthScore: 62.4,
        tnfdStatus: 'High Threat Action Area'
      }
    ];
  }

  calculateTotalPopulation(taxa = this.taxa) {
    if (!taxa || taxa.length === 0) return 0;
    return taxa.reduce((acc, t) => acc + t.observedPopulation, 0);
  }

  calculateAverageBioacousticScore(taxa = this.taxa) {
    if (!taxa || taxa.length === 0) return 0.0;
    const sum = taxa.reduce((acc, t) => acc + t.bioacousticHealthScore, 0);
    return parseFloat((sum / taxa.length).toFixed(1));
  }

  filterTaxa(criteria) {
    return this.taxa.filter(t => {
      if (criteria.biome && criteria.biome !== 'ALL' && t.biome !== criteria.biome) return false;
      if (criteria.iucnCategory && criteria.iucnCategory !== 'ALL' && t.iucnCategory !== criteria.iucnCategory) return false;
      if (criteria.searchQuery && criteria.searchQuery.trim() !== '') {
        const query = criteria.searchQuery.toLowerCase().trim();
        if (!t.speciesCode.toLowerCase().includes(query) && !t.taxonName.toLowerCase().includes(query)) return false;
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
