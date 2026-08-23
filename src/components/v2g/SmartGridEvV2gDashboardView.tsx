import React, { useState } from 'react';

export interface EvChargerItem {
  chargerId: string;
  stationName: string;
  chargerType: string;
  connectorStandard: string;
  powerRatingKw: number;
  currentPowerKw: number;
  evVin: string;
  batteryCapacityKwh: number;
  socPct: number;
  targetSocPct: number;
  v2gActive: boolean;
  gridFeedinKw: number;
  revenueUsd: number;
}

export interface EvDepotHub {
  hubId: string;
  hubName: string;
  location: string;
  gridOperator: string;
  transformerCapacityKva: number;
  currentDemandKw: number;
  totalV2gDischargeKwh: number;
  carbonAvoidedKg: number;
  chargers: EvChargerItem[];
}

export const SmartGridEvV2gDashboardView: React.FC = () => {
  const [hubs] = useState<EvDepotHub[]>([
    {
      hubId: 'HUB-V2G-801',
      hubName: 'San Francisco Transit Fleet V2G Hub',
      location: 'San Francisco, California',
      gridOperator: 'Pacific Gas & Electric (PG&E)',
      transformerCapacityKva: 2500,
      currentDemandKw: 850,
      totalV2gDischargeKwh: 4850,
      carbonAvoidedKg: 3210,
      chargers: [
        {
          chargerId: 'V2G-CHG-01',
          stationName: 'Depot Alpha Bay 1 (DC Fast V2G)',
          chargerType: 'DC_FAST_V2G',
          connectorStandard: 'CCS2_ISO15118',
          powerRatingKw: 150,
          currentPowerKw: 120,
          evVin: '1FTVW1EL8NW009102',
          batteryCapacityKwh: 131,
          socPct: 85,
          targetSocPct: 90,
          v2gActive: true,
          gridFeedinKw: 80,
          revenueUsd: 42.5,
        },
        {
          chargerId: 'V2G-CHG-02',
          stationName: 'Depot Alpha Bay 2 (Level 2 Bi-Dir)',
          chargerType: 'LEVEL_2_BIDIRECTIONAL',
          connectorStandard: 'NACS_BIDIRECTIONAL',
          powerRatingKw: 19.2,
          currentPowerKw: 15,
          evVin: '5YJ3E1EA7KF891023',
          batteryCapacityKwh: 82,
          socPct: 92,
          targetSocPct: 80,
          v2gActive: true,
          gridFeedinKw: 12.5,
          revenueUsd: 18.2,
        },
      ],
    },
  ]);

  const [selectedHub, setSelectedHub] = useState<EvDepotHub | null>(null);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-10 font-sans space-y-8">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 border-b border-slate-800 pb-6">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <span className="bg-blue-500/10 text-blue-400 border border-blue-500/20 text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider">
              Smart Grid & V2G Optimization
            </span>
            <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-bold px-3 py-1 rounded-full font-mono">
              ISO 15118 & OCPP 2.0.1 Ready
            </span>
          </div>
          <h1 className="text-3xl md:text-4xl font-black text-white tracking-tight">
            Enterprise Smart Grid EV V2G Optimization Studio
          </h1>
          <p className="text-sm text-slate-400 mt-1 max-w-3xl">
            Bidirectional vehicle-to-grid (V2G) fleet dispatch, ISO 15118 smart charging, and frequency response monetization.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {hubs.map((hub) => (
          <div key={hub.hubId} className="bg-slate-900/80 backdrop-blur-md border border-slate-800 rounded-2xl p-6 shadow-xl">
            <div className="flex justify-between items-center mb-3">
              <span className="text-xs font-mono font-bold text-slate-400 bg-slate-950 px-2.5 py-1 rounded border border-slate-800">
                {hub.hubId}
              </span>
              <span className="text-xs font-bold px-3 py-1 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/30">
                {hub.gridOperator}
              </span>
            </div>
            <h3 className="text-xl font-black text-white mb-1">{hub.hubName}</h3>
            <p className="text-xs text-slate-400 mb-4">{hub.location}</p>

            <div className="grid grid-cols-2 gap-3 bg-slate-950/60 p-3.5 rounded-xl border border-slate-800 mb-4">
              <div>
                <span className="text-[11px] text-slate-400 block">Discharge Total</span>
                <span className="text-lg font-black text-emerald-400">{hub.totalV2gDischargeKwh} kWh</span>
              </div>
              <div>
                <span className="text-[11px] text-slate-400 block">Carbon Avoided</span>
                <span className="text-lg font-black text-blue-400">{hub.carbonAvoidedKg} kg</span>
              </div>
            </div>

            <button
              onClick={() => setSelectedHub(hub)}
              className="w-full py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs rounded-xl transition-all"
            >
              Inspect V2G Fleet Telemetry
            </button>
          </div>
        ))}
      </div>

      {selectedHub && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-xl w-full space-y-4">
            <h2 className="text-xl font-bold text-white">{selectedHub.hubName} Telemetry</h2>
            {selectedHub.chargers.map((chg, idx) => (
              <div key={idx} className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 text-xs space-y-1">
                <div className="flex justify-between font-bold text-blue-400">
                  <span>{chg.stationName} [{chg.chargerType}]</span>
                  <span>{chg.gridFeedinKw} kW V2G</span>
                </div>
                <p className="text-slate-400">VIN: {chg.evVin} | Battery SoC: {chg.socPct}% | Revenue: ${chg.revenueUsd.toFixed(2)}</p>
              </div>
            ))}
            <button
              onClick={() => setSelectedHub(null)}
              className="w-full py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs rounded-xl"
            >
              Close Telemetry
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
