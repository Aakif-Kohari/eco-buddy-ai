/**
 * @file WasteDashboard.tsx
 * @description Master architectural envelope wrapping the entire Circular Economy Trackers UI suite.
 * Injects context providers, handles massive ESG data states, and constructs a responsive
 * dashboard leveraging heavy Tailwind/Framer capabilities out-of-the-box.
 */

import React from 'react';
import { motion } from 'framer-motion';
import { PackageOpen, Activity, Compass, Target, BadgeCheck, AlertTriangle } from 'lucide-react';
import { WasteDataProvider, useWasteData } from './WasteDataService';
import { CircularFlowDiagram } from './CircularFlowDiagram';
import { DisposalFacilityTable } from './DisposalFacilityTable';
import { formatWeightKg } from './WasteCoreTypes';

const WasteDashboardContent: React.FC = () => {
    const { enterpriseStats, isLoading, error, refreshData } = useWasteData();

    if (isLoading || !enterpriseStats) {
        return (
            <div className="w-full flex h-[70vh] flex-col items-center justify-center font-sans">
                <PackageOpen className="w-16 h-16 text-emerald-500 animate-pulse mb-6 opacity-80" />
                <h3 className="text-lg font-bold text-slate-600 dark:text-slate-300">Synchronizing Global Waste Ledgers...</h3>
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-10 w-full max-w-2xl mx-auto mt-20 text-center bg-white dark:bg-slate-800 rounded-3xl border border-red-500/20 shadow-2xl font-sans">
                <AlertTriangle className="w-16 h-16 text-red-500 mx-auto mb-4" />
                <h3 className="text-2xl font-black text-slate-800 dark:text-white mb-2">Sync Sequence Failed</h3>
                <p className="text-slate-500 dark:text-slate-400 mb-8">{error}</p>
                <button onClick={refreshData} className="px-6 py-2.5 bg-red-500 hover:bg-red-600 text-white font-bold rounded-xl shadow-md transition-colors">
                    Re-initialize Subsystem
                </button>
            </div>
        );
    }

    const {
        totalWasteVolumeTons,
        globalDiversionRate,
        topWasteCategory,
        totalDisposalCost,
        certifiedContractorsRatio,
        scope3WasteEmissions
    } = enterpriseStats;

    return (
        <div className="w-full max-w-7xl mx-auto p-4 sm:p-8 pb-32 space-y-8 font-sans">

            <header className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-slate-200 dark:border-slate-700/50 pb-6 mb-2">
                <div>
                    <h2 className="text-3xl md:text-4xl font-black text-slate-900 dark:text-white flex items-center gap-3 tracking-tighter">
                        <PackageOpen className="w-10 h-10 text-emerald-500" />
                        Circular Economy Tracker
                    </h2>
                    <p className="text-slate-500 dark:text-slate-400 mt-2 font-medium max-w-2xl">
                        End-to-end telemetry on corporate disposal workflows. Optimizing zero-waste-to-landfill trajectory mapping compliant with global GHG frameworks.
                    </p>
                </div>
                <div className="flex gap-2">
                    <button className="px-4 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 font-bold text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors shadow-sm">
                        Export LCA PDF
                    </button>
                </div>
            </header>

            {/* Top KPI Metrics Array */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">

                <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
                    className="bg-gradient-to-br from-emerald-500 to-teal-600 rounded-3xl p-6 text-white shadow-lg relative overflow-hidden"
                >
                    <div className="absolute -right-4 -bottom-4 opacity-20">
                        <Target className="w-32 h-32" />
                    </div>
                    <div className="relative z-10">
                        <h4 className="font-bold mb-1 opacity-90 text-sm">Global Diversion Rate</h4>
                        <div className="flex items-baseline gap-1 mt-2">
                            <span className="text-5xl font-black tracking-tighter">{globalDiversionRate.toFixed(1)}</span>
                            <span className="text-xl font-bold opacity-80">%</span>
                        </div>
                        <p className="text-xs font-medium mt-4 bg-black/20 inline-block px-2 py-1 rounded">Target 2030: 95% Diversion</p>
                    </div>
                </motion.div>

                {[
                    { label: 'Scope 3 Est', val: scope3WasteEmissions.toFixed(0), unit: 'tCO2e', icon: Activity, color: 'text-orange-500 bg-orange-500/10' },
                    { label: 'Total Output Volume', val: totalWasteVolumeTons.toFixed(1), unit: 'Tons', icon: Compass, color: 'text-blue-500 bg-blue-500/10' },
                    { label: 'Certified Vendor Ratio', val: `${certifiedContractorsRatio.toFixed(0)}%`, unit: 'Compliance', icon: BadgeCheck, color: 'text-purple-500 bg-purple-500/10' },
                ].map((kpi, idx) => (
                    <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.2 + (idx * 0.1) }}
                        key={kpi.label}
                        className="bg-white dark:bg-slate-800/80 backdrop-blur-xl border border-slate-200 dark:border-slate-700/50 rounded-3xl p-6 shadow-sm flex flex-col justify-between"
                    >
                        <div className="flex justify-between items-start mb-4">
                            <h4 className="text-slate-500 dark:text-slate-400 font-bold text-sm tracking-tight w-2/3">{kpi.label}</h4>
                            <div className={`p-2 rounded-xl ${kpi.color}`}>
                                <kpi.icon className="w-5 h-5" />
                            </div>
                        </div>
                        <div className="flex items-baseline gap-1">
                            <span className="text-3xl font-black text-slate-800 dark:text-white tracking-tighter">{kpi.val}</span>
                            <span className="text-[10px] font-bold text-slate-400 uppercase">{kpi.unit}</span>
                        </div>
                    </motion.div>
                ))}
            </div>

            {/* Intelligent Dual-Paned Analysis Layout */}
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">

                <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.4 }} className="xl:col-span-1">
                    <div className="bg-white dark:bg-slate-800/80 backdrop-blur-xl border border-slate-200 dark:border-slate-700/50 rounded-3xl p-1 h-full shadow-sm">
                        <CircularFlowDiagram />
                    </div>
                </motion.div>

                <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.5 }} className="xl:col-span-2">
                    <div className="bg-white dark:bg-slate-800/80 backdrop-blur-xl border border-slate-200 dark:border-slate-700/50 rounded-3xl p-1 h-full shadow-sm flex flex-col justify-center px-10 border-l-[10px] border-l-emerald-500">
                        <h3 className="text-2xl font-black text-slate-800 dark:text-white mb-2">Automated ESG Insight</h3>
                        <p className="text-slate-600 dark:text-slate-300 leading-relaxed font-medium mb-6">
                            The algorithm has detected that <span className="font-bold text-emerald-600 dark:text-emerald-400">{topWasteCategory}</span> is currently your heaviest output waste vector by sheer mass.
                            However, the cost of disposal implies inefficiencies.
                        </p>

                        <div className="p-4 bg-slate-50 dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 flex gap-4">
                            <div className="flex-1">
                                <h5 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">Financial Run-Rate</h5>
                                <div className="text-xl font-bold font-mono text-slate-800 dark:text-white">${totalDisposalCost.toLocaleString()} <span className="text-sm font-sans font-normal text-slate-500">YTD</span></div>
                            </div>
                            <div className="w-px bg-slate-200 dark:bg-slate-700"></div>
                            <div className="flex-1">
                                <h5 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">Recommendation</h5>
                                <div className="text-sm font-semibold text-emerald-600 dark:text-emerald-400">Negotiate secondary stream upcycling. Expected NPV +$45k.</div>
                            </div>
                        </div>
                    </div>
                </motion.div>

            </div>

            {/* Lower Manifest Datagrid */}
            <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.6 }}>
                <DisposalFacilityTable />
            </motion.div>

        </div>
    );
};

/**
 * Root Entrypoint rendering the global DataProvider context around the child hierarchy
 */
export const WasteDashboard: React.FC = () => {
    return (
        <WasteDataProvider>
            <WasteDashboardContent />
        </WasteDataProvider>
    );
};

export default WasteDashboard;
