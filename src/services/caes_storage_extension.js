/**
 * Compressed Air Energy Storage Analytics & Expansion Functions
 */

function calculateDischargeTurbinePower(airMassFlowKgSec, expansionRatioTotal, heatInletTempC = 550) {
  // Expansion power W_exp = m_dot * c_p * T_in * [ 1 - (1 / PR)^((k-1)/k) ]
  const cP = 1.005; // kJ/(kg·K)
  const tInK = heatInletTempC + 273.15;
  const k = 1.4;
  const exponent = (k - 1) / k;

  const powerKw = airMassFlowKgSec * cP * tInK * (1 - Math.pow(1 / expansionRatioTotal, exponent));
  const powerMw = powerKw / 1000;

  return {
    airMassFlowKgSec,
    expansionRatioTotal,
    turbineInletTempC: heatInletTempC,
    turbineOutputMW: Math.round(powerMw * 100) / 100,
  };
}

function calculateCavernAirMassTonnes(cavernVolumeM3, pressureBar, tempC = 40) {
  // Ideal gas law: m = (P * V) / (R * T)
  const pressurePa = pressureBar * 100000;
  const tempK = tempC + 273.15;
  const rGas = 287; // J/(kg·K)

  const massKg = (pressurePa * cavernVolumeM3) / (rGas * tempK);
  return Math.round((massKg / 1000) * 10) / 10;
}

module.exports = {
  calculateDischargeTurbinePower,
  calculateCavernAirMassTonnes,
};
