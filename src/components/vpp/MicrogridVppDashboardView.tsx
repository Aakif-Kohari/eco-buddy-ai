import React, { useState } from 'react';

export interface DerAsset {
  assetId: string;
  assetName: string;
  assetType: 'SOLAR_PV' | 'BESS' | 'WIND_TURBINE' | 'EV_BIDIRECTIONAL';
  capacityKw: number;
  currentOutputKw: number;
  socPct: number;
  status: string;
}

export interface MicrogridFacility {
  facilityId: string;
  facilityName: string;
  location: string;
  gridStatus: string;
  totalCapacityKw: number;
  currentLoadKw: number;
  renewableFractionPct: number;
  savingsUsd: number;
  assets: DerAsset[];
}

export const MicrogridVppDashboardView: React.FC = () => {
  const [facilities] = useState<MicrogridFacility[]>([
    {
      facilityId: 'GRID-VPP-701',
      facilityName: 'Apex Enterprise Sustainability Campus',
      location: 'Austin, Texas',
      gridStatus: 'ISLANDED_OPTIMIZED',
      totalCapacityKw: 5100,
      currentLoadKw: 2800,
      renewableFractionPct: 94.2,
      savingsUsd: 14250,
      assets: [
        {
          assetId: 'DER-BESS-01',
          assetName: 'Tesla Megapack 2XL Battery Bank',
          assetType: 'BESS',
          capacityKw: 2500,
          currentOutputKw: 1200,
          socPct: 88.5,
          status: 'DISPATCHING',
        },
        {
          assetId: 'DER-SOLAR-02',
          assetName: 'Rooftop Bifacial Solar PV Array',
          assetType: 'SOLAR_PV',
          capacityKw: 1800,
          currentOutputKw: 1650,
          socPct: 100,
          status: 'MAX_GENERATION',
        },
      ],
    },
  ]);

  const [selectedFacility, setSelectedFacility] = useState<MicrogridFacility | null>(null);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-10 font-sans space-y-8">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 border-b border-slate-800 pb-6">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <span className="bg-amber-500/10 text-amber-400 border border-amber-500/20 text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider">
              VPP Dispatch Network
            </span>
            <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-bold px-3 py-1 rounded-full font-mono">
              IEEE 1547 Microgrid Compliant
            </span>
          </div>
          <h1 className="text-3xl md:text-4xl font-black text-white tracking-tight">
            Enterprise Microgrid & Virtual Power Plant (VPP) Studio
          </h1>
          <p className="text-sm text-slate-400 mt-1 max-w-3xl">
            Real-time battery storage dispatch, solar PV telemetry, and grid-tied peak shaving optimization.
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
              <span className="text-xs font-bold px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                {fac.gridStatus}
              </span>
            </div>
            <h3 className="text-xl font-black text-white mb-1">{fac.facilityName}</h3>
            <p className="text-xs text-slate-400 mb-4">{fac.location}</p>

            <div className="grid grid-cols-2 gap-3 bg-slate-950/60 p-3.5 rounded-xl border border-slate-800 mb-4">
              <div>
                <span className="text-[11px] text-slate-400 block">VPP Capacity</span>
                <span className="text-lg font-black text-amber-400">{fac.totalCapacityKw} kW</span>
              </div>
              <div>
                <span className="text-[11px] text-slate-400 block">Renewable Fraction</span>
                <span className="text-lg font-black text-emerald-400">{fac.renewableFractionPct}%</span>
              </div>
            </div>

            <button
              onClick={() => setSelectedFacility(fac)}
              className="w-full py-2.5 bg-amber-600 hover:bg-amber-500 text-white font-bold text-xs rounded-xl transition-all"
            >
              Dispatch & Inspect DER Telemetry
            </button>
          </div>
        ))}
      </div>

      {selectedFacility && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-xl w-full space-y-4">
            <h2 className="text-xl font-bold text-white">{selectedFacility.facilityName} DER Telemetry</h2>
            {selectedFacility.assets.map((asset, idx) => (
              <div key={idx} className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 text-xs space-y-1">
                <div className="flex justify-between font-bold text-amber-400">
                  <span>{asset.assetName} [{asset.assetType}]</span>
                  <span>{asset.currentOutputKw} / {asset.capacityKw} kW</span>
                </div>
                <p className="text-slate-400">Status: {asset.status} | Battery SoC: {asset.socPct}%</p>
              </div>
            ))}
            <button
              onClick={() => setSelectedFacility(null)}
              className="w-full py-2.5 bg-amber-600 hover:bg-amber-500 text-white font-bold text-xs rounded-xl"
            >
              Close Telemetry
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
