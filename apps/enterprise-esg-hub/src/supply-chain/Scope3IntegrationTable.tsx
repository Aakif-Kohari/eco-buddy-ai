import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Filter, ShieldAlert, CheckCircle, Database } from 'lucide-react';
import { useSupplierRisk } from './SupplierRiskService';
import { getHexAliasForTailwind, formatCurrency } from './SupplyChainCoreTypes';

const Scope3IntegrationTable: React.FC = () => {
    const { nodes } = useSupplierRisk();
    const [search, setSearch] = useState('');

    const filteredNodes = nodes.filter(n => n.name.toLowerCase().includes(search.toLowerCase()) || n.id.toLowerCase().includes(search.toLowerCase()));

    return (
        <div className="w-full flex flex-col h-full bg-transparent font-sans">
            <div className="p-5 flex flex-col sm:flex-row justify-between items-center gap-4 bg-slate-50 dark:bg-slate-800/40 border-b border-slate-200 dark:border-slate-700/50">
                <div>
                    <h3 className="text-lg font-bold text-slate-800 dark:text-white">Supplier Audit & Validation Ledger</h3>
                </div>
                <div className="relative w-full sm:w-80">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                        <Search className="h-4 w-4 text-slate-400" />
                    </div>
                    <input
                        type="text"
                        placeholder="Search vendors by name or ID..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="block w-full pl-10 pr-3 py-2 border border-slate-200 dark:border-slate-700 rounded-xl bg-white dark:bg-slate-900 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 sm:text-sm"
                    />
                </div>
            </div>

            <div className="overflow-x-auto w-full">
                <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-700">
                    <thead className="bg-slate-50 dark:bg-slate-800/80">
                        <tr>
                            <th className="px-6 py-4 text-left text-xs font-bold text-slate-500 uppercase tracking-wider">Vendor ID / Name</th>
                            <th className="px-6 py-4 text-left text-xs font-bold text-slate-500 uppercase tracking-wider">Location</th>
                            <th className="px-6 py-4 text-left text-xs font-bold text-slate-500 uppercase tracking-wider">Scope 3 Em.</th>
                            <th className="px-6 py-4 text-left text-xs font-bold text-slate-500 uppercase tracking-wider">Risk Level</th>
                            <th className="px-6 py-4 text-left text-xs font-bold text-slate-500 uppercase tracking-wider">Audit Score</th>
                        </tr>
                    </thead>
                    <tbody className="bg-white dark:bg-slate-900/40 divide-y divide-slate-200 dark:divide-slate-700/50">
                        <AnimatePresence>
                            {filteredNodes.map((n, i) => (
                                <motion.tr
                                    key={n.id}
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0 }}
                                    transition={{ delay: i * 0.05 }}
                                    className="hover:bg-slate-50 dark:hover:bg-slate-800/60 group"
                                >
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <div className="flex flex-col">
                                            <span className="text-sm font-bold text-slate-900 dark:text-white">{n.name}</span>
                                            <span className="text-xs font-mono text-slate-500">{n.id} • {n.tier}</span>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600 dark:text-slate-300">
                                        <div className="flex items-center gap-1.5">
                                            {n.country}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <span className="text-sm font-mono font-bold text-slate-700 dark:text-slate-200">
                                            {n.metrics.scope3Emissions.toLocaleString()} <span className="text-xs text-slate-500 font-sans">tCO2e</span>
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <span className={`px-2.5 py-1 text-xs font-bold rounded-full border ${getHexAliasForTailwind(n.risk)}`}>
                                            {n.risk}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <div className="flex items-center gap-2">
                                            <div className="w-16 h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                                                <div
                                                    className={`h-full ${n.metrics.auditScore > 80 ? 'bg-emerald-500' : n.metrics.auditScore > 50 ? 'bg-amber-500' : 'bg-red-500'}`}
                                                    style={{ width: `${n.metrics.auditScore}%` }}
                                                ></div>
                                            </div>
                                            <span className="text-xs font-bold text-slate-600 dark:text-slate-400">{n.metrics.auditScore}/100</span>
                                        </div>
                                    </td>
                                </motion.tr>
                            ))}
                        </AnimatePresence>
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default Scope3IntegrationTable;
