/**
 * @file DisposalFacilityTable.tsx
 * @description Master paginated reporting table to outline all tracked Enterprise Waste Flow vectors.
 * Implements advanced Lucide icon state logic and full Tailwind Responsive Tables.
 */

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Filter, ShieldCheck, FileWarning, Factory, MoreHorizontal, FileText } from 'lucide-react';
import { useWasteData } from './WasteDataService';
import { formatWeightKg, getCategoryBadgeStyle } from './WasteCoreTypes';

export const DisposalFacilityTable: React.FC = () => {
    const { manifests, isLoading } = useWasteData();
    const [search, setSearch] = useState('');

    if (isLoading) {
        return (
            <div className="w-full bg-white dark:bg-slate-800/80 rounded-2xl h-80 flex items-center justify-center border border-slate-200 dark:border-slate-700/50">
                <div className="flex flex-col items-center">
                    <div className="w-10 h-10 rounded-full border-4 border-slate-200 border-t-slate-800 dark:border-slate-700 dark:border-t-white animate-spin"></div>
                    <span className="mt-3 text-sm font-medium text-slate-500">Retrieving Manifest Audits...</span>
                </div>
            </div>
        );
    }

    const filteredManifests = manifests.filter(m =>
        m.manifestId.toLowerCase().includes(search.toLowerCase()) ||
        m.originFacilityId.toLowerCase().includes(search.toLowerCase()) ||
        m.destinationProvider.toLowerCase().includes(search.toLowerCase())
    );

    return (
        <div className="w-full bg-white dark:bg-slate-800/80 backdrop-blur-xl border border-slate-200 dark:border-slate-700/50 rounded-2xl shadow-sm overflow-hidden flex flex-col font-sans">

            <div className="p-5 border-b border-slate-200 dark:border-slate-700/50 flex flex-col md:flex-row justify-between items-center gap-4 bg-slate-50/50 dark:bg-slate-900/40">
                <div>
                    <h3 className="text-lg font-bold text-slate-800 dark:text-white flex items-center gap-2">
                        <FileText className="w-5 h-5 text-slate-400" />
                        Disposal Audit Ledger
                    </h3>
                    <p className="text-xs font-medium text-slate-500 mt-1">Immutable transaction ledger of processed waste material loads.</p>
                </div>

                <div className="relative w-full md:w-80">
                    <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
                    <input
                        type="text"
                        placeholder="Search ID, Facility, or Vendor..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-xl pl-9 pr-3 py-2 w-full text-sm font-medium text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-shadow transition-colors"
                    />
                </div>
            </div>

            <div className="overflow-x-auto w-full">
                <table className="w-full text-left border-collapse">
                    <thead className="bg-slate-100 dark:bg-slate-800/50">
                        <tr>
                            <th className="px-6 py-4 font-bold text-xs uppercase tracking-wider text-slate-500 border-b border-slate-200 dark:border-slate-700">Manifest TRK</th>
                            <th className="px-6 py-4 font-bold text-xs uppercase tracking-wider text-slate-500 border-b border-slate-200 dark:border-slate-700">Category & Type</th>
                            <th className="px-6 py-4 font-bold text-xs uppercase tracking-wider text-slate-500 border-b border-slate-200 dark:border-slate-700">Routing & Vendor</th>
                            <th className="px-6 py-4 font-bold text-xs uppercase tracking-wider text-slate-500 border-b border-slate-200 dark:border-slate-700">Metrics</th>
                            <th className="px-6 py-4 font-bold text-xs uppercase tracking-wider text-slate-500 border-b border-slate-200 dark:border-slate-700 text-center">Compliance</th>
                            <th className="px-6 py-4 border-b border-slate-200 dark:border-slate-700"></th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-700/50">
                        <AnimatePresence>
                            {filteredManifests.length > 0 ? (
                                filteredManifests.map((row, i) => (
                                    <motion.tr
                                        initial={{ opacity: 0, y: 15 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        exit={{ opacity: 0 }}
                                        transition={{ delay: i * 0.05 }}
                                        key={row.manifestId}
                                        className="hover:bg-slate-50 dark:hover:bg-slate-700/40 transition-colors group"
                                    >
                                        <td className="px-6 py-4 align-top whitespace-nowrap">
                                            <div className="flex flex-col">
                                                <span className="font-extrabold font-mono text-slate-800 dark:text-white mb-1 group-hover:text-emerald-500 transition-colors cursor-pointer">
                                                    #{row.manifestId}
                                                </span>
                                                <span className="text-[10px] uppercase font-bold text-slate-400">
                                                    {new Date(row.timestamp).toLocaleDateString()}
                                                </span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 align-top whitespace-nowrap">
                                            <div className="flex flex-col items-start gap-1.5">
                                                <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold tracking-widest border ${getCategoryBadgeStyle(row.category)}`}>
                                                    {row.category}
                                                </span>
                                                <span className="text-sm font-semibold text-slate-600 dark:text-slate-300">
                                                    {row.disposalMethod}
                                                </span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 align-top">
                                            <div className="flex flex-col text-sm font-medium">
                                                <div className="flex items-center text-slate-800 dark:text-slate-200 mb-1">
                                                    <Factory className="w-3.5 h-3.5 mr-1.5 text-slate-400" />
                                                    {row.originFacilityId}
                                                </div>
                                                <div className="text-slate-500 dark:text-slate-400 text-xs flex items-center">
                                                    <span className="w-1 h-1 bg-slate-300 dark:bg-slate-600 rounded-full mr-2 ml-1"></span>
                                                    Exp: {row.destinationProvider}
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 align-top whitespace-nowrap">
                                            <div className="text-lg font-black font-mono text-slate-800 dark:text-white">
                                                {formatWeightKg(row.weightKg)}
                                            </div>
                                            <div className="text-[10px] font-bold text-slate-400 uppercase mt-0.5">
                                                ${row.costUsd.toFixed(2)} Cost
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 align-middle text-center whitespace-nowrap">
                                            {row.certified ? (
                                                <span className="inline-flex items-center justify-center p-2 rounded-full bg-emerald-100 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400" title="Valid Certificates on File">
                                                    <ShieldCheck className="w-5 h-5" />
                                                </span>
                                            ) : (
                                                <span className="inline-flex items-center justify-center p-2 rounded-full bg-red-100 dark:bg-red-500/20 text-red-600 dark:text-red-400" title="Missing Validation Forms">
                                                    <FileWarning className="w-5 h-5" />
                                                </span>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 align-middle text-right">
                                            <button className="p-2 text-slate-400 hover:text-emerald-600 bg-transparent hover:bg-emerald-50 dark:hover:bg-emerald-500/10 rounded-lg transition-colors outline-none cursor-pointer">
                                                <MoreHorizontal className="w-5 h-5" />
                                            </button>
                                        </td>
                                    </motion.tr>
                                ))
                            ) : (
                                <tr>
                                    <td colSpan={6} className="px-6 py-12 text-center">
                                        <Filter className="w-12 h-12 text-slate-200 dark:text-slate-700 mx-auto mb-3" />
                                        <span className="text-slate-500 font-medium block">No ledger entries found matching constraints.</span>
                                    </td>
                                </tr>
                            )}
                        </AnimatePresence>
                    </tbody>
                </table>
            </div>

            <div className="px-6 py-4 bg-slate-50/80 dark:bg-slate-900/40 border-t border-slate-200 dark:border-slate-700/50 flex justify-between items-center text-xs font-bold text-slate-500">
                <span>Displaying {filteredManifests.length} manifest records.</span>
                <span className="uppercase tracking-widest">End of ledger block</span>
            </div>
        </div>
    );
};

export default DisposalFacilityTable;
