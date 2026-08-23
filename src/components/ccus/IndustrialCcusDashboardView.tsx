import React, { useState } from 'react';

export interface CcusUnitItem {
  unitId: string;
  unitName: string;
  technologyType: string;
  flueGasFlowM3Hr: number;
  co2ConcentrationPct: number;
  captureEfficiencyPct: number;
  dailyCapturedTons: number;
  operatingStatus: string;
}

export interface CcusPlantFacility {
  facilityId: string;
  facilityName: string;
  industrySector: string;
  location: str if False else string;
  annualGrossTons: number;
  annualNetCapturedTons: number;
  sequestrationMethod: string;
  taxOffsetUsd: number;
  units: CcusUnitItem[];
}

export const IndustrialCcusDashboardView: React.FC = () => {
  const [plants] = useState<CcusPlantFacility[]>([
    {
      facilityId: 'PLANT-CCUS-901',
      facilityName: 'Apex Green Cement & Materials Facility',
      industrySector: 'CEMENT_MANUFACTURING',
      location: 'Houston, Texas',
      annualGrossTons: 450000,
      annualNetCapturedTons: 380000,
      sequestrationMethod: 'DEEP_SALINE_AQUIFER',
      taxOffsetUsd: 32300000,
      units: [
        {
          unitId: 'CCUS-UNIT-01',
          unitName: 'Amine Solvent Flue Gas Absorber Column A',
          technologyType: 'AMINE_SOLVENT_ABSORPTION',
          flueGasFlowM3Hr: 120000,
          co2ConcentrationPct: 14.5,
          captureEfficiencyPct: 92.8,
          dailyCapturedTons: 480,
          operatingStatus: 'OPTIMAL_ABSORPTION',
        },
        {
          unitId: 'CCUS-UNIT-02',
          unitName: 'Modular Direct Air Capture (DAC) Collector Array',
          technologyType: 'DIRECT_AIR_CAPTURE_DAC',
          flueGasFlowM3Hr: 450000,
          co2ConcentrationPct: 0.04,
          captureEfficiencyPct: 88.0,
          dailyCapturedTons: 125,
          operatingStatus: 'THERMAL_DESORPTION',
        },
      ],
    },
  ]);

  const [selectedPlant, setSelectedPlant] = useState<CcusPlantFacility | null>(null);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-10 font-sans space-y-8">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 border-b border-slate-800 pb-6">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <span className="bg-purple-500/10 text-purple-400 border border-purple-500/20 text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider">
              Industrial CCUS & Sequestration
            </span>
            <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-bold px-3 py-1 rounded-full font-mono">
              EPA Class VI & 45Q Tax Credit Verified
            </span>
          </div>
          <h1 className="text-3xl md:text-4xl font-black text-white tracking-tight">
            Enterprise Industrial CCUS & Carbon Capture Studio
          </h1>
          <p className="text-sm text-slate-400 mt-1 max-w-3xl">
            Flue gas CO2 absorption telemetry, Direct Air Capture (DAC) operational monitoring, and geological sequestration tracking.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {plants.map((plant) => (
          <div key={plant.facilityId} className="bg-slate-900/80 backdrop-blur-md border border-slate-800 rounded-2xl p-6 shadow-xl">
            <div className="flex justify-between items-center mb-3">
              <span className="text-xs font-mono font-bold text-slate-400 bg-slate-950 px-2.5 py-1 rounded border border-slate-800">
                {plant.facilityId}
              </span>
              <span className="text-xs font-bold px-3 py-1 rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/30">
                {plant.industrySector}
              </span>
            </div>
            <h3 className="text-xl font-black text-white mb-1">{plant.facilityName}</h3>
            <p className="text-xs text-slate-400 mb-4">{plant.location} • Method: {plant.sequestrationMethod}</p>

            <div className="grid grid-cols-2 gap-3 bg-slate-950/60 p-3.5 rounded-xl border border-slate-800 mb-4">
              <div>
                <span className="text-[11px] text-slate-400 block">Captured CO2</span>
                <span className="text-lg font-black text-emerald-400">{plant.annualNetCapturedTons.toLocaleString()} Tons/yr</span>
              </div>
              <div>
                <span className="text-[11px] text-slate-400 block">45Q Tax Credit</span>
                <span className="text-lg font-black text-purple-400">${(plant.taxOffsetUsd / 1000000).toFixed(1)}M</span>
              </div>
            </div>

            <button
              onClick={() => setSelectedPlant(plant)}
              className="w-full py-2.5 bg-purple-600 hover:bg-purple-500 text-white font-bold text-xs rounded-xl transition-all"
            >
              Inspect Capture Units Telemetry
            </button>
          </div>
        ))}
      </div>

      {selectedPlant && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-xl w-full space-y-4">
            <h2 className="text-xl font-bold text-white">{selectedPlant.facilityName} Capture Units</h2>
            {selectedPlant.units.map((unit, idx) => (
              <div key={idx} className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 text-xs space-y-1">
                <div className="flex justify-between font-bold text-purple-400">
                  <span>{unit.unitName} [{unit.technologyType}]</span>
                  <span>{unit.dailyCapturedTons} Tons/day</span>
                </div>
                <p className="text-slate-400">Status: {unit.operatingStatus} | Efficiency: {unit.captureEfficiencyPct}%</p>
              </div>
            ))}
            <button
              onClick={() => setSelectedPlant(null)}
              className="w-full py-2.5 bg-purple-600 hover:bg-purple-500 text-white font-bold text-xs rounded-xl"
            >
              Close Telemetry
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
