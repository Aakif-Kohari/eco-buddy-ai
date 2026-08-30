/**
 * Waste Heat Thermoelectric Generator Analytics Extension
 */

function calculateArrayPowerOutput(singleModuleWatts, totalModulesCount) {
  const totalPowerWatts = singleModuleWatts * totalModulesCount;
  const totalPowerKw = totalPowerWatts / 1000;
  return {
    totalModulesCount,
    totalArrayPowerWatts: Math.round(totalPowerWatts),
    totalArrayPowerKw: Math.round(totalPowerKw * 100) / 100,
  };
}

function calculateAnnualCo2SavingsFromHarvest(dailyHarvestKwh, gridEmissionsKgCo2Kwh = 0.45) {
  const annualKwh = dailyHarvestKwh * 365;
  const annualCo2Kg = annualKwh * gridEmissionsKgCo2Kwh;
  const annualCo2Tonnes = annualCo2Kg / 1000;
  return {
    annualKwhHarvested: Math.round(annualKwh),
    annualCo2OffsetTonnes: Math.round(annualCo2Tonnes * 100) / 100,
  };
}

module.exports = {
  calculateArrayPowerOutput,
  calculateAnnualCo2SavingsFromHarvest,
};
