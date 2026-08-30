/**
 * Additional Water Recycling Telemetry Extension & Analytics Helpers
 */

function calculateSludgeProductionRate(influentFlowM3, tssMgL) {
  // Dry Sludge (kg/day) = Flow (m³/day) * TSS (mg/L) / 1000
  const drySludgeKg = (influentFlowM3 * tssMgL) / 1000;
  const wetSludgeTonnesAt20Pct = (drySludgeKg / 0.20) / 1000;
  return {
    drySludgeKgDay: Math.round(drySludgeKg),
    wetSludgeTonnesDay: Math.round(wetSludgeTonnesAt20Pct * 10) / 10,
  };
}

function evaluateChemicalDosingRates(influentFlowM3) {
  // Coagulant (Alum): 25 mg/L, Flocculant (Polymer): 2 mg/L
  const alumKgDay = (influentFlowM3 * 25) / 1000;
  const polymerKgDay = (influentFlowM3 * 2) / 1000;
  return {
    alumCoagulantKgDay: Math.round(alumKgDay),
    polymerFlocculantKgDay: Math.round(polymerKgDay),
  };
}

module.exports = {
  calculateSludgeProductionRate,
  evaluateChemicalDosingRates,
};
