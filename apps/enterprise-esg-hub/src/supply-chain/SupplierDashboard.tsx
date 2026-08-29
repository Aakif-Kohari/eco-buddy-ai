import React from 'react';
import { motion } from 'framer-motion';
import { Globe, AlertTriangle, Layers, Activity, Truck, Cpu, Network } from 'lucide-react';
import { useSupplierRisk } from './SupplierRiskService';
import { formatCurrency, getHexAliasForTailwind } from './SupplyChainCoreTypes';
import Scope3IntegrationTable from './Scope3IntegrationTable';
import SupplierNodeGraph from './SupplierNodeGraph';

const SupplierDashboard: React.FC = () => {
    const { summary, isLoading, error, refreshData } = useSupplierRisk();

    if (isLoading) {
        return (
            <div className="flex flex-col items-center justify-center w-full min-h-[500px]">
                <div className="w-12 h-12 border-4 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin"></div>
                <p className="mt-4 text-slate-500 dark:text-slate-400">Mapping Global Supply Chain...</p>
            </div>
        );
    }

    if (error || !summary) {
        return (
            <div className="p-8 bg-red-50 dark:bg-red-500/10 rounded-2xl w-full text-center">
                <AlertTriangle className="w-10 h-10 text-red-500 mx-auto mb-3" />
                <h3 className="text-xl font-bold text-red-700 dark:text-red-400">Analyzer Initialization Failed</h3>
                <button onClick={refreshData} className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg">Retry Sync</button>
            </div>
        );
    }

    return (
        <div className="p-8 pb-32 max-w-7xl mx-auto space-y-8 w-full font-sans">
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div>
                    <h2 className="text-3xl font-extrabold text-slate-800 dark:text-white tracking-tight flex items-center gap-3">
                        <Network className="w-8 h-8 text-emerald-500" />
                        AI Supply Chain Analyzer
                    </h2>
                    <p className="mt-2 text-slate-500 dark:text-slate-400">
                        Topological risk mapping & Scope 3 automated diagnostics for enterprise vendor networks.
                    </p>
                </div>
            </div>

            {/* AI Top KPIs Card Layout */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {[
                    { label: 'Network Nodes', val: summary.totalSuppliers.toString(), icon: Layers, gradient: 'from-blue-500 to-cyan-400', txtColor: 'text-blue-500' },
                    { label: 'Scope 3 Trace', val: `${(summary.totalScope3Emissions / 1000).toFixed(1)}k`, suffix: 'tCO2e', icon: Activity, gradient: 'from-emerald-500 to-teal-400', txtColor: 'text-emerald-500' },
                    { label: 'Critical Risks', val: summary.highRiskCount.toString(), icon: AlertTriangle, gradient: 'from-orange-500 to-red-400', txtColor: 'text-orange-500', pulse: true },
                    { label: 'Data Quality Index', val: `${summary.averageDataQuality.toFixed(0)}%`, icon: Cpu, gradient: 'from-purple-500 to-indigo-400', txtColor: 'text-purple-500' }
                ].map((k, i) => (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.1 }}
                        key={k.label}
                        className="bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/50 backdrop-blur-xl p-6 rounded-2xl relative overflow-hidden group"
                    >
                        <div className={`absolute top-0 right-0 w-24 h-24 bg-gradient-to-br ${k.gradient} opacity-10 rounded-full blur-2xl -mr-8 -mt-8 group-hover:scale-150 transition-transform duration-500`}></div>
                        <div className={`mb-4 inline-flex p-3 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-100 dark:border-slate-800 ${k.pulse ? 'animate-pulse' : ''}`}>
                            <k.icon className={`w-6 h-6 ${k.txtColor}`} />
                        </div>
                        <h4 className="text-slate-500 dark:text-slate-400 font-medium text-sm mb-1">{k.label}</h4>
                        <div className="flex items-baseline gap-1">
                            <span className="text-3xl font-black text-slate-800 dark:text-white tracking-tighter">{k.val}</span>
                            {k.suffix && <span className="text-sm font-semibold text-slate-400">{k.suffix}</span>}
                        </div>
                    </motion.div>
                ))}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Advanced Graph Viz */}
                <motion.div
                    initial={{ opacity: 0, scale: 0.98 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.3 }}
                    className="lg:col-span-2 bg-white dark:bg-slate-800/80 backdrop-blur-xl border border-slate-200 dark:border-slate-700/50 rounded-2xl shadow-sm p-6 flex flex-col h-[600px]"
                >
                    <div className="mb-4">
                        <h3 className="text-lg font-bold text-slate-800 dark:text-white">Dependency Topology Matrix</h3>
                        <p className="text-sm text-slate-500">Tier 1-3 AI-generated upstream lineage</p>
                    </div>
                    <div className="flex-1 w-full bg-slate-50 dark:bg-slate-900/50 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden relative">
                        <SupplierNodeGraph />
                    </div>
                </motion.div>

                {/* Insights Panel */}
                <motion.div
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.4 }}
                    className="bg-white dark:bg-slate-800/80 backdrop-blur-xl border border-slate-200 dark:border-slate-700/50 rounded-2xl shadow-sm p-6"
                >
                    <h3 className="text-lg font-bold text-slate-800 dark:text-white mb-6">AI Diagnostics Log</h3>

                    <div className="space-y-4">
                        <div className="p-4 rounded-xl bg-orange-50 dark:bg-orange-500/10 border border-orange-200 dark:border-orange-500/20">
                            <div className="flex gap-3">
                                <AlertTriangle className="w-5 h-5 text-orange-500 flex-shrink-0" />
                                <div>
                                    <h4 className="text-sm font-bold text-orange-700 dark:text-orange-400">Tier 2 Bottleneck Detected</h4>
                                    <p className="text-xs text-orange-600 dark:text-orange-300 mt-1 leading-relaxed">
                                        "SinoTech Materials" carries critical risk status. 45% of Tier 1 suppliers rely on this single node, representing an aggregated $35M revenue risk path.
                                    </p>
                                </div>
                            </div>
                        </div>

                        <div className="p-4 rounded-xl bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/20">
                            <div className="flex gap-3">
                                <Globe className="w-5 h-5 text-emerald-500 flex-shrink-0" />
                                <div>
                                    <h4 className="text-sm font-bold text-emerald-700 dark:text-emerald-400">Decarbonization Opportunity</h4>
                                    <p className="text-xs text-emerald-600 dark:text-emerald-300 mt-1 leading-relaxed">
                                        Shifting logistics from "Oceanic Shipping" to "Nordic Packaging" routes could reduce upstream transportation emissions by approximately 18% YoY.
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                </motion.div>
            </div>

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
                className="bg-white dark:bg-slate-800/80 backdrop-blur-xl border border-slate-200 dark:border-slate-700/50 rounded-2xl shadow-sm overflow-hidden"
            >
                <Scope3IntegrationTable />
            </motion.div>

        </div>
    );
};

export default SupplierDashboard;
