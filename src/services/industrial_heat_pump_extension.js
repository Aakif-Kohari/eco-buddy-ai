/**
 * Industrial Heat Pump Waste Heat Integration Extension
 */

function calculateHeatExchangerEfficiency(hotInletTempC, hotOutletTempC, coldInletTempC) {
  // Effectiveness (ε) = (T_hot_in - T_hot_out) / (T_hot_in - T_cold_in)
  const tempDiffMax = hotInletTempC - coldInletTempC;
  if (tempDiffMax <= 0) return 0;
  const effectiveness = (hotInletTempC - hotOutletTempC) / tempDiffMax;
  return Math.round(effectiveness * 100) / 100;
}

function estimateThermalStorageTankSizeM3(thermalLoadKw, hoursBuffer) {
  // Water specific heat capacity c_p = 4.184 kJ/kg·K (1.162 Wh/kg·K)
  // Assuming ΔT = 40°C temperature swing in storage tank
  const energyRequiredKwh = thermalLoadKw * hoursBuffer;
  const waterKg = (energyRequiredKwh * 1000) / (1.162 * 40);
  const volumeM3 = waterKg / 1000;
  return Math.round(volumeM3);
}

module.exports = {
  calculateHeatExchangerEfficiency,
  estimateThermalStorageTankSizeM3,
};
