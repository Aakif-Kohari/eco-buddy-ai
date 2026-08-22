/**
 * @file FleetDashboard.tsx
 * @description Main Parent UI Layout orchestrating all nested Fleet Tracking widgets, 
 * integrating the core context provider, and displaying the critical ESG metrics for
 * modern highly responsive dark-mode compliance.
 */

import React from 'react';
import { motion } from 'framer-motion';
import { Truck, Navigation2, Zap, AlertOctagon, TrendingDown, Factory } from 'lucide-react';
import { useFleetData } from './FleetDataService';
import { EvChargingOptimizer } from './EvChargingOptimizer';
import { VehicleStatusTable } from './VehicleStatusTable';

export const FleetDashboardContent: React.FC = () => {
    const { aggregates, isLoading, error, forceSync } = useFleetData();

    if (isLoading || !aggregates) {
        return (
            <div className="flex w-full h-[80vh] flex-col items-center justify-center">
                <div className="w-16 h-16 rounded-3xl border-4 text-emerald-500 border-emerald-500/30 border-t-emerald-500 animate-spin shadow-[0_0_40px_-10px_rgba(16,185,129,0.5)]"></div>
                <h3 className="mt-6 text-xl font-bold text-slate-700 dark:text-slate-300 animate-pulse tracking-wide">Initializing Global Fleet Uplink...</h3>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex w-full h-[80vh] flex-col items-center justify-center bg-slate-50 dark:bg-slate-900 border border-red-500/20 m-6 rounded-3xl">
                <AlertOctagon className="w-16 h-16 text-red-500 mb-4 animate-bounce" />
                <h3 className="text-2xl font-black text-red-500 tracking-tight mb-2">TELEMETRY LINK FAULT</h3>
                <p className="text-slate-500 dark:text-slate-400 mb-6 font-medium">{error}</p>
                <button
                    onClick={forceSync}
                    className="px-8 py-3 bg-red-500 hover:bg-red-600 text-white font-bold rounded-xl shadow-lg transition-transform hover:scale-105 active:scale-95"
                >
                    Re-establish Connection
                </button>
            </div>
        );
    }

    const {
        totalVehicles,
        zeroEmissionVehicles,
        totalDailyDistanceMiles,
        fleetWideEfficiencyScore,
        dailyCarbonEmissions,
        activeChargingCount,
        criticalAlertsTotal
    } = aggregates;

    const zevPercentage = totalVehicles > 0 ? (zeroEmissionVehicles / totalVehicles) * 100 : 0;

    return (
        <div className="w-full max-w-7xl mx-auto p-8 pb-32 space-y-10 font-sans">

            {/* Title Block */}
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div>
                    <h2 className="text-4xl font-extrabold text-slate-900 dark:text-white tracking-tighter flex items-center gap-3">
                        <Truck className="w-10 h-10 text-emerald-500" />
                        Green Mobility Hub
                    </h2>
                    <p className="text-slate-500 dark:text-slate-400 mt-2 font-medium">
                        Live ESG telemetry monitoring, Scope 1 fleet accounting, and AI smart routing engine.
                    </p>
                </div>
            </div>

            {/* Top KPI Banner */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">

                {/* Large Specialty KPI */}
                <motion.div
                    initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}
                    className="lg:col-span-2 bg-gradient-to-br from-slate-900 to-slate-800 dark:from-slate-950 dark:to-slate-900 border border-slate-700/50 p-6 rounded-3xl shadow-2xl relative overflow-hidden"
                >
                    <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-500/20 rounded-full blur-3xl -mr-20 -mt-20"></div>
                    <div className="relative z-10 flex flex-col h-full justify-between">
                        <div>
                            <div className="inline-flex items-center px-2.5 py-1 bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 text-xs font-bold rounded-full mb-3 uppercase tracking-wider">
                                Global Target 2030
                            </div>
                            <h3 className="text-slate-400 font-medium mb-1">Zero Emission Ratio (ZEV)</h3>
                            <div className="flex items-baseline gap-2">
                                <span className="text-5xl font-black text-white tracking-tighter">{zevPercentage.toFixed(0)}%</span>
                            </div>
                        </div>
                        <div className="mt-8">
                            <div className="flex justify-between text-xs font-bold text-slate-400 mb-2 uppercase tracking-widest">
                                <span>{zeroEmissionVehicles} ZEV</span>
                                <span>{totalVehicles - zeroEmissionVehicles} ICE/HEV</span>
                            </div>
                            <div className="w-full h-2.5 bg-slate-800 rounded-full overflow-hidden">
                                <motion.div
                                    initial={{ width: 0 }} animate={{ width: `${zevPercentage}%` }} transition={{ delay: 0.5, duration: 1, type: "spring" }}
                                    className="h-full bg-emerald-500 rounded-full"
                                />
                            </div>
                        </div>
                    </div>
                </motion.div>

                {/* Secondary KPIs */}
                {[
                    { label: 'Scope 1 Daily Burn', val: dailyCarbonEmissions.toFixed(1), suffix: 'tCO2e', icon: Factory, color: 'text-red-500', trend: <TrendingDown className="w-4 h-4 mr-1" />, statInfo: '4.2% DoD decrease' },
                    { label: 'Active Grid Charging', val: activeChargingCount, suffix: 'Units', icon: Zap, color: 'text-blue-500' },
                    { label: 'Network Distance', val: `${(totalDailyDistanceMiles / 1000).toFixed(1)}k`, suffix: 'Mi', icon: Navigation2, color: 'text-indigo-500' }
                ].map((k, i) => (
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.2 + (i * 0.1) }}
                        key={k.label}
                        className="bg-white dark:bg-slate-800/80 backdrop-blur-xl border border-slate-200 dark:border-slate-700/50 p-6 rounded-3xl shadow-sm flex flex-col justify-between"
                    >
                        <div>
                            <div className="flex items-center justify-between mb-4">
                                <div className={`p-2.5 rounded-xl bg-slate-50 dark:bg-slate-900 shadow-inner ${k.color}`}>
                                    <k.icon className="w-6 h-6" />
                                </div>
                                {k.trend && (
                                    <span className="flex items-center text-[10px] font-bold text-emerald-600 bg-emerald-100 dark:bg-emerald-500/20 dark:text-emerald-400 px-2 py-1 rounded-full border border-emerald-500/20">
                                        {k.trend} {k.statInfo}
                                    </span>
                                )}
                            </div>
                            <h4 className="text-slate-500 dark:text-slate-400 font-bold text-sm tracking-wide">{k.label}</h4>
                        </div>
                        <div className="flex items-baseline gap-1 mt-3">
                            <span className="text-3xl font-black text-slate-800 dark:text-white tracking-tighter">{k.val}</span>
                            <span className="text-sm font-bold text-slate-400">{k.suffix}</span>
                        </div>
                    </motion.div>
                ))}
            </div>

            {/* Smart Charging Integrator */}
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
                <EvChargingOptimizer />
            </motion.div>

            {/* Live Telemetry Data Table */}
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}>
                <div className="flex items-center justify-between mb-2">
                    <h3 className="text-xl font-bold flex items-center text-slate-800 dark:text-white">
                        <span className="w-3 h-3 bg-red-500 rounded-full mr-3 animate-pulse shadow-[0_0_10px_-1px_rgba(239,68,68,0.8)]"></span>
                        Live Telemetry Uplink
                    </h3>
                    {criticalAlertsTotal > 0 && (
                        <div className="bg-red-100 text-red-600 border border-red-500/30 px-3 py-1 rounded-lg text-xs font-bold flex items-center shadow-sm">
                            <AlertOctagon className="w-3 h-3 mr-1" /> {criticalAlertsTotal} Critical Alerts Isolated
                        </div>
                    )}
                </div>
                <VehicleStatusTable />
            </motion.div>

        </div>
    );
};

// Exporting a Wrapped component directly inside this file to avoid complex imports
import { FleetDataProvider } from './FleetDataService';
export const FleetDashboard: React.FC = () => (
    <FleetDataProvider>
        <FleetDashboardContent />
    </FleetDataProvider>
);

export default FleetDashboard;
