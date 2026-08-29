import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, Factory, Wind, Zap, Fingerprint } from 'lucide-react';
import { useEsgMetrics } from '../services/EsgMetricsService';
import EsgEmissionsChart from './EsgEmissionsChart';
import EsgDataTable from './EsgDataTable';

export const EsgDashboardContainer: React.FC = () => {
    const {
        kpiData,
        isLoading,
        error,
        fetchMetrics,
        timelineData,
        transactions
    } = useEsgMetrics();

    // Container variants for staggered entrance
    const containerVariants = {
        hidden: { opacity: 0 },
        show: {
            opacity: 1,
            transition: { staggerChildren: 0.1 }
        }
    };

    const itemVariants = {
        hidden: { opacity: 0, y: 20 },
        show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 24 } }
    };

    if (isLoading) {
        return (
            <div className="flex flex-col items-center justify-center w-full h-full min-h-[600px]">
                <div className="w-16 h-16 border-4 border-emerald-500/20 border-t-emerald-500 rounded-full animate-spin shadow-lg"></div>
                <p className="mt-6 text-slate-500 dark:text-slate-400 font-medium animate-pulse">Aggregating Enterprise ESG Data...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-8 m-8 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30 rounded-2xl">
                <h3 className="text-xl font-bold text-red-700 dark:text-red-400 mb-2">Error Loading ESG Data</h3>
                <p className="text-red-600 dark:text-red-300 mb-4">{error}</p>
                <button
                    onClick={fetchMetrics}
                    className="px-6 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg shadow-md transition-colors"
                >
                    Retry Connection
                </button>
            </div>
        );
    }

    const cards = [
        {
            id: 'scope1',
            title: 'Scope 1 Emissions',
            value: kpiData?.scope1.toLocaleString() ?? '424,500',
            unit: 'tCO2e',
            trend: -4.2,
            icon: Factory,
            color: 'from-emerald-500 to-teal-400',
            bg: 'bg-emerald-500/10'
        },
        {
            id: 'scope2',
            title: 'Scope 2 Emissions',
            value: kpiData?.scope2.toLocaleString() ?? '112,300',
            unit: 'tCO2e',
            trend: -6.8,
            icon: Zap,
            color: 'from-blue-500 to-indigo-400',
            bg: 'bg-blue-500/10'
        },
        {
            id: 'scope3',
            title: 'Scope 3 Trajectory',
            value: kpiData?.scope3.toLocaleString() ?? '1,894,200',
            unit: 'tCO2e',
            trend: +2.1,
            icon: Wind,
            color: 'from-orange-500 to-amber-400',
            bg: 'bg-orange-500/10'
        },
        {
            id: 'footprint',
            title: 'Carbon Intensity',
            value: kpiData?.intensity.toFixed(2) ?? '14.2',
            unit: 'tCO2e / $M Rev',
            trend: -12.5,
            icon: Fingerprint,
            color: 'from-purple-500 to-fuchsia-400',
            bg: 'bg-purple-500/10'
        },
    ];

    return (
        <div className="p-8 pb-32 max-w-7xl mx-auto space-y-8">

            {/* Header Section */}
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div>
                    <h2 className="text-3xl font-bold font-display text-slate-800 dark:text-white tracking-tight">Enterprise Environmental Insights</h2>
                    <p className="mt-2 text-slate-500 dark:text-slate-400">Deep-dive analytics into corporate carbon accounting and sustainability metrics.</p>
                </div>

                <div className="flex items-center gap-3">
                    <button className="px-5 py-2.5 rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 font-medium hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors shadow-sm">
                        Export Report
                    </button>
                    <button className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 text-white font-medium shadow-md shadow-emerald-500/20 transition-all hover:shadow-lg hover:-translate-y-0.5">
                        Generate Strategy
                    </button>
                </div>
            </div>

            {/* KPIs Grid */}
            <motion.div
                variants={containerVariants}
                initial="hidden"
                animate="show"
                className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6"
            >
                {cards.map((card) => {
                    const Icon = card.icon;
                    const isPositiveTrend = card.trend < 0; // Negative emissions trend is positive context!
                    return (
                        <motion.div
                            key={card.id}
                            variants={itemVariants}
                            className="bg-white dark:bg-slate-800/80 backdrop-blur-xl border border-slate-200 dark:border-slate-700/50 rounded-2xl p-6 shadow-sm hover:shadow-xl transition-all duration-300 relative overflow-hidden group"
                        >
                            <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br opacity-5 rounded-full blur-3xl -mr-10 -mt-10 group-hover:opacity-20 transition-opacity duration-500"></div>

                            <div className="flex justify-between items-start mb-6 relative">
                                <div className={`p-3 rounded-xl ${card.bg} text-transparent bg-clip-text bg-gradient-to-br ${card.color}`}>
                                    <Icon className="w-7 h-7 stroke-current" />
                                </div>
                                <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-sm font-semibold border
                                    ${isPositiveTrend
                                        ? 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-200/50 dark:border-emerald-500/20'
                                        : 'bg-red-50 dark:bg-red-500/10 text-red-600 dark:text-red-400 border-red-200/50 dark:border-red-500/20'}`
                                }>
                                    {isPositiveTrend ? <TrendingDown className="w-4 h-4" /> : <TrendingUp className="w-4 h-4" />}
                                    {Math.abs(card.trend)}%
                                </div>
                            </div>

                            <div className="relative">
                                <h3 className="text-slate-500 dark:text-slate-400 font-medium mb-1">{card.title}</h3>
                                <div className="flex items-baseline gap-2">
                                    <span className="text-3xl font-extrabold text-slate-800 dark:text-white tracking-tight">
                                        {card.value}
                                    </span>
                                    <span className="text-sm font-medium text-slate-400 dark:text-slate-500 font-mono">
                                        {card.unit}
                                    </span>
                                </div>
                            </div>
                        </motion.div>
                    );
                })}
            </motion.div>

            {/* Main Content Layout */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Chart Section */}
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.3, duration: 0.4 }}
                    className="lg:col-span-2 bg-white dark:bg-slate-800/80 backdrop-blur-xl border border-slate-200 dark:border-slate-700/50 rounded-2xl p-6 shadow-sm flex flex-col"
                >
                    <div className="flex items-center justify-between mb-8">
                        <div>
                            <h3 className="text-lg font-bold text-slate-800 dark:text-white">Historical Emissions Matrix</h3>
                            <p className="text-sm text-slate-500 break-words mt-1">Multi-scope trajectory modeling (2018 - Present)</p>
                        </div>
                        <select className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 rounded-lg px-4 py-2 text-sm font-medium focus:ring-2 focus:ring-emerald-500 outline-none transition-shadow">
                            <option>Last 5 Years</option>
                            <option>Last 10 Years</option>
                            <option>Year-to-Date</option>
                        </select>
                    </div>

                    {/* Integrated Chart Component */}
                    <div className="flex-1 w-full min-h-[350px]">
                        <EsgEmissionsChart data={timelineData} />
                    </div>
                </motion.div>

                {/* Vertical Data Summary */}
                <motion.div
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.4, duration: 0.4 }}
                    className="relative bg-gradient-to-b from-slate-800 to-slate-900 dark:from-slate-900 dark:to-slate-950 rounded-2xl p-6 text-white shadow-xl shadow-slate-900/20 overflow-hidden"
                >
                    <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-500/20 rounded-full blur-3xl -mr-20 -mt-20"></div>
                    <div className="relative z-10">
                        <h3 className="text-lg font-bold text-white mb-2">Portfolio Assessment</h3>
                        <p className="text-slate-400 text-sm mb-6 pb-6 border-b border-white/10">AI-driven confidence rating based on data completeness.</p>

                        <div className="space-y-6">
                            {[
                                { label: 'Data Completeness', val: 94, color: 'bg-emerald-500' },
                                { label: 'Assurance Confidence', val: 82, color: 'bg-teal-400' },
                                { label: 'Reduction Target Alignment', val: 67, color: 'bg-amber-400' }
                            ].map((item, idx) => (
                                <div key={idx} className="space-y-2">
                                    <div className="flex justify-between text-sm">
                                        <span className="font-medium text-slate-200">{item.label}</span>
                                        <span className="font-bold text-white">{item.val}%</span>
                                    </div>
                                    <div className="h-2.5 w-full bg-slate-800 rounded-full overflow-hidden shadow-inner">
                                        <motion.div
                                            initial={{ width: 0 }}
                                            animate={{ width: `${item.val}%` }}
                                            transition={{ duration: 1, delay: 0.5 + (idx * 0.2) }}
                                            className={`h-full ${item.color} rounded-full`}
                                        />
                                    </div>
                                </div>
                            ))}
                        </div>

                        <div className="mt-10 p-5 bg-white/5 border border-white/10 rounded-xl backdrop-blur-md relative overflow-hidden group hover:bg-white/10 transition-colors">
                            <h4 className="font-semibold text-emerald-400 mb-1">AI Recommendation</h4>
                            <p className="text-sm text-slate-300 leading-relaxed">
                                Optimizing your Supply Chain (Scope 3) logistics path via Route 9b could reduce transportation emissions by an estimated 12.4% YoY.
                            </p>
                        </div>
                    </div>
                </motion.div>
            </div>

            {/* Unified Data Table section */}
            <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.6, duration: 0.5 }}
                className="bg-white dark:bg-slate-800/80 backdrop-blur-xl border border-slate-200 dark:border-slate-700/50 rounded-2xl shadow-sm overflow-hidden flex flex-col"
            >
                <div className="p-6 border-b border-slate-200 dark:border-slate-700/50 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                        <h3 className="text-lg font-bold text-slate-800 dark:text-white">Recent Carbon Offset Transactions</h3>
                        <p className="text-sm text-slate-500 mt-1">Detailed ledger of verified offsets and renewable energy credits.</p>
                    </div>
                </div>

                <div className="flex-1 w-full">
                    <EsgDataTable transactions={transactions} />
                </div>
            </motion.div>

        </div>
    );
};

export default EsgDashboardContainer;
