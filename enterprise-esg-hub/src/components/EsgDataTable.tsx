import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Search,
    Filter,
    MoreHorizontal,
    CheckCircle2,
    AlertCircle,
    Clock,
    ArrowUpDown,
    DownloadCloud
} from 'lucide-react';

export interface OffsetTransaction {
    id: string;
    date: string;
    project: string;
    type: 'Forestry' | 'Renewable Energy' | 'Methane Capture' | 'Direct Air Capture';
    amount: number; // tCO2e
    status: 'Verified' | 'Pending' | 'Failed';
    provider: string;
}

interface EsgDataTableProps {
    transactions: OffsetTransaction[];
}

export const EsgDataTable: React.FC<EsgDataTableProps> = ({ transactions }) => {
    const [searchTerm, setSearchTerm] = useState('');
    const [sortField, setSortField] = useState<keyof OffsetTransaction>('date');
    const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
    const [statusFilter, setStatusFilter] = useState<string>('All');

    // Handle Sorting Logic
    const handleSort = (field: keyof OffsetTransaction) => {
        if (sortField === field) {
            setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
        } else {
            setSortField(field);
            setSortDirection('desc');
        }
    };

    // Filter AND Sort combinations
    const processedData = transactions
        .filter(t => t.project.toLowerCase().includes(searchTerm.toLowerCase()) || t.provider.toLowerCase().includes(searchTerm.toLowerCase()))
        .filter(t => statusFilter === 'All' || t.status === statusFilter)
        .sort((a, b) => {
            let aVal = a[sortField];
            let bVal = b[sortField];

            if (typeof aVal === 'string' && typeof bVal === 'string') {
                return sortDirection === 'asc'
                    ? aVal.localeCompare(bVal)
                    : bVal.localeCompare(aVal);
            }
            if (typeof aVal === 'number' && typeof bVal === 'number') {
                return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
            }
            return 0;
        });

    const getStatusStyle = (status: string) => {
        switch (status) {
            case 'Verified': return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400 border-emerald-200 dark:border-emerald-500/30';
            case 'Pending': return 'bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400 border-amber-200 dark:border-amber-500/30';
            case 'Failed': return 'bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400 border-red-200 dark:border-red-500/30';
            default: return 'bg-slate-100 text-slate-700 dark:bg-slate-500/20 dark:text-slate-400';
        }
    };

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'Verified': return <CheckCircle2 className="w-3.5 h-3.5 mr-1.5 inline" />;
            case 'Pending': return <Clock className="w-3.5 h-3.5 mr-1.5 inline" />;
            case 'Failed': return <AlertCircle className="w-3.5 h-3.5 mr-1.5 inline" />;
            default: return null;
        }
    };

    const getTypeColor = (type: string) => {
        switch (type) {
            case 'Forestry': return 'text-emerald-500';
            case 'Renewable Energy': return 'text-yellow-500';
            case 'Methane Capture': return 'text-orange-500';
            case 'Direct Air Capture': return 'text-blue-500';
            default: return 'text-slate-500';
        }
    }

    return (
        <div className="w-full flex flex-col h-full bg-transparent">
            {/* Table High-level Controls */}
            <div className="p-4 flex flex-col sm:flex-row justify-between items-center gap-4 bg-slate-50 dark:bg-slate-800/40 border-b border-slate-200 dark:border-slate-700/50">
                <div className="relative w-full sm:w-80">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                        <Search className="h-4 w-4 text-slate-400" />
                    </div>
                    <input
                        type="text"
                        placeholder="Search projects or providers..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="block w-full pl-10 pr-3 py-2 border border-slate-200 dark:border-slate-700 rounded-xl leading-5 bg-white dark:bg-slate-900 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 sm:text-sm transition-all"
                    />
                </div>

                <div className="flex items-center gap-3 w-full sm:w-auto">
                    <div className="relative flex-1 sm:flex-none">
                        <select
                            value={statusFilter}
                            onChange={(e) => setStatusFilter(e.target.value)}
                            className="appearance-none w-full pl-3 pr-10 py-2 border border-slate-200 dark:border-slate-700 rounded-xl bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 font-medium text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                        >
                            <option value="All">All Statuses</option>
                            <option value="Verified">Verified</option>
                            <option value="Pending">Pending</option>
                            <option value="Failed">Failed</option>
                        </select>
                        <Filter className="absolute right-3 top-2.5 h-4 w-4 text-slate-400 pointer-events-none" />
                    </div>

                    <button className="flex items-center justify-center gap-2 px-4 py-2 border border-slate-200 dark:border-slate-700 rounded-xl bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 font-medium text-sm transition-colors cursor-pointer outline-none">
                        <DownloadCloud className="w-4 h-4" />
                        <span>CSV</span>
                    </button>
                </div>
            </div>

            {/* Responsive Table Container */}
            <div className="overflow-x-auto w-full">
                <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-700">
                    <thead className="bg-slate-50 dark:bg-slate-800/80">
                        <tr>
                            {['id', 'project', 'type', 'amount', 'date', 'status'].map((header: string) => (
                                <th
                                    key={header}
                                    scope="col"
                                    className="px-6 py-4 text-left text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-700/50 transition-colors select-none"
                                    onClick={() => handleSort(header as keyof OffsetTransaction)}
                                >
                                    <div className="flex items-center gap-2">
                                        {header === 'id' ? 'Trx ID' : header}
                                        {sortField === header && (
                                            <ArrowUpDown className={`w-3 h-3 ${sortDirection === 'desc' ? 'text-emerald-500' : 'text-slate-400'}`} />
                                        )}
                                    </div>
                                </th>
                            ))}
                            <th scope="col" className="relative px-6 py-4">
                                <span className="sr-only">Actions</span>
                            </th>
                        </tr>
                    </thead>
                    <tbody className="bg-white dark:bg-slate-900/40 divide-y divide-slate-200 dark:divide-slate-700/50">
                        <AnimatePresence>
                            {processedData.length > 0 ? (
                                processedData.map((tx: OffsetTransaction, idx: number) => (
                                    <motion.tr
                                        key={tx.id}
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        exit={{ opacity: 0 }}
                                        transition={{ delay: idx * 0.05 }}
                                        className="hover:bg-slate-50 dark:hover:bg-slate-800/60 transition-colors group"
                                    >
                                        <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-slate-500 dark:text-slate-400">
                                            #{tx.id}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="flex items-center">
                                                <div>
                                                    <div className="text-sm font-bold text-slate-900 dark:text-white group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors">{tx.project}</div>
                                                    <div className="text-xs text-slate-500 dark:text-slate-400">{tx.provider}</div>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="flex items-center text-sm font-medium">
                                                <span className={`w-2 h-2 rounded-full mr-2 ${getTypeColor(tx.type).replace('text-', 'bg-')}`}></span>
                                                <span className="text-slate-700 dark:text-slate-300">{tx.type}</span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className="text-sm font-bold font-mono text-slate-900 dark:text-white">
                                                {tx.amount.toLocaleString()} <span className="text-xs text-slate-500 font-sans">tCO2e</span>
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500 dark:text-slate-400">
                                            {tx.date}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold border ${getStatusStyle(tx.status)}`}>
                                                {getStatusIcon(tx.status)}
                                                {tx.status}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                            <button className="text-slate-400 hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700">
                                                <MoreHorizontal className="w-5 h-5" />
                                            </button>
                                        </td>
                                    </motion.tr>
                                ))
                            ) : (
                                <tr>
                                    <td colSpan={7} className="px-6 py-12 text-center text-slate-500 dark:text-slate-400">
                                        <div className="flex flex-col items-center justify-center space-y-3">
                                            <Search className="w-10 h-10 opacity-20" />
                                            <p className="text-base font-medium">No transactions found matching your criteria.</p>
                                            <p className="text-sm">Try adjusting your search terms or filters.</p>
                                        </div>
                                    </td>
                                </tr>
                            )}
                        </AnimatePresence>
                    </tbody>
                </table>
            </div>

            {/* Pagination / Footer */}
            <div className="px-6 py-4 border-t border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/50 flex items-center justify-between text-sm text-slate-500 dark:text-slate-400">
                <span>Showing <span className="font-bold text-slate-700 dark:text-slate-300">{processedData.length}</span> of {transactions.length} entries</span>
                <div className="flex gap-2">
                    <button className="px-4 py-2 border border-slate-200 dark:border-slate-700 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors disabled:opacity-50" disabled>Previous</button>
                    <button className="px-4 py-2 bg-emerald-500 text-white rounded-lg hover:bg-emerald-600 transition-colors shadow-sm shadow-emerald-500/20">Next</button>
                </div>
            </div>
        </div>
    );
};

export default EsgDataTable;
