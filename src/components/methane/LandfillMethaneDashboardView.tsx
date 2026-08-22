import React, { useState } from 'react';

export interface WellheadSensor {
  wellId: string;
  wellName: string;
  ch4Pct: number;
  co2Pct: number;
  o2Pct: number;
  flowCfm: number;
  vacuumInWc: number;
  status: string;
}

export interface LandfillFacility {
  facilityId: string;
  facilityName: string;
  location: string;
  areaAcres: number;
  wasteTons: number;
  fugitiveCh4KgHr: number;
  rngMcfDay: number;
  creditsUsd: number;
  wellheads: WellheadSensor[];
}

export const LandfillMethaneDashboardView: React.FC = () => {
  const [facilities] = useState<LandfillFacility[]>([
    {
      facilityId: 'LF-CH4-401',
      facilityName: 'Apex EcoLandfill Renewable Natural Gas Plant',
      location: 'Phoenix, Arizona',
      areaAcres: 420,
      wasteTons: 12500000,
      fugitiveCh4KgHr: 85.4,
      rngMcfDay: 3200,
      creditsUsd: 18500,
      wellheads: [
        {
          wellId: 'WELL-CH4-01',
          wellName: 'Sector A North Wellhead 14',
          ch4Pct: 56.4,
          co2Pct: 41.2,
          o2Pct: 0.4,
          flowCfm: 145,
          vacuumInWc: -12.5,
          status: 'OPTIMAL_EXTRACTION',
        },
        {
          wellId: 'WELL-CH4-02',
          wellName: 'Sector B West Wellhead 09',
          ch4Pct: 52.1,
          co2Pct: 43.8,
          o2Pct: 1.8,
          flowCfm: 98,
          vacuumInWc: -8.2,
          status: 'AIR_INTRUSION_RISK',
        },
      ],
    },
  ]);

  const [selectedFac, setSelectedFac] = useState<LandfillFacility | null>(null);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-10 font-sans space-y-8">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 border-b border-slate-800 pb-6">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <span className="bg-orange-500/10 text-orange-400 border border-orange-500/20 text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider">
              Landfill Methane & RNG Recovery
            </span>
            <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-bold px-3 py-1 rounded-full font-mono">
              EPA Subpart HH & RIN Certified
            </span>
          </div>
          <h1 className="text-3xl md:text-4xl font-black text-white tracking-tight">
            Enterprise Landfill Methane Recovery Studio
          </h1>
          <p className="text-sm text-slate-400 mt-1 max-w-3xl">
            Real-time CH4 fugitive emissions tracking, gas wellhead vacuum tuning, and Renewable Natural Gas (RNG) grid injection.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {facilities.map((fac) => (
          <div key={fac.facilityId} className="bg-slate-900/80 backdrop-blur-md border border-slate-800 rounded-2xl p-6 shadow-xl">
            <div className="flex justify-between items-center mb-3">
              <span className="text-xs font-mono font-bold text-slate-400 bg-slate-950 px-2.5 py-1 rounded border border-slate-800">
                {fac.facilityId}
              </span>
              <span className="text-xs font-bold px-3 py-1 rounded-full bg-orange-500/10 text-orange-400 border border-orange-500/30">
                {fac.areaAcres} Acres
              </span>
            </div>
            <h3 className="text-xl font-black text-white mb-1">{fac.facilityName}</h3>
            <p className="text-xs text-slate-400 mb-4">{fac.location}</p>

            <div className="grid grid-cols-2 gap-3 bg-slate-950/60 p-3.5 rounded-xl border border-slate-800 mb-4">
              <div>
                <span className="text-[11px] text-slate-400 block">Pipeline RNG Output</span>
                <span className="text-lg font-black text-emerald-400">{fac.rngMcfDay.toLocaleString()} MCF/day</span>
              </div>
              <div>
                <span className="text-[11px] text-slate-400 block">RIN & Offset Value</span>
                <span className="text-lg font-black text-orange-400">${fac.creditsUsd.toLocaleString()}</span>
              </div>
            </div>

            <button
              onClick={() => setSelectedFac(fac)}
              className="w-full py-2.5 bg-orange-600 hover:bg-orange-500 text-white font-bold text-xs rounded-xl transition-all"
            >
              Inspect Wellhead Sensor Matrix
            </button>
          </div>
        ))}
      </div>

      {selectedFac && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-xl w-full space-y-4">
            <h2 className="text-xl font-bold text-white">{selectedFac.facilityName} Sensors</h2>
            {selectedFac.wellheads.map((w, idx) => (
              <div key={idx} className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 text-xs space-y-1">
                <div className="flex justify-between font-bold text-orange-400">
                  <span>{w.wellName}</span>
                  <span>{w.flowCfm} CFM</span>
                </div>
                <p className="text-slate-400">CH4: {w.ch4Pct}% | CO2: {w.co2Pct}% | O2: {w.o2Pct}% | Vacuum: {w.vacuumInWc} in. W.C.</p>
              </div>
            ))}
            <button
              onClick={() => setSelectedFac(null)}
              className="w-full py-2.5 bg-orange-600 hover:bg-orange-500 text-white font-bold text-xs rounded-xl"
            >
              Close Telemetry
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
