/**
 * @file EvChargingOptimizer.tsx
 * @description Advanced React Component orchestrating a simulation of an EV charging
 * schedule. Utilizes Grid Carbon Intensity localized metrics to schedule "Green Charging"
 * hours to minimize grid carbon impact under the scope 2 accounting protocol.
 */

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Zap, Clock, Calendar, BarChart3, CloudRain, AlertCircle, Play, Settings } from 'lucide-react';
import { useFleetData } from './FleetDataService';

/**
 * Mock data struct for Hourly Grid Intensity forecast
 */
const intensityForecast = [
    { hour: '12:00', intensity: 450, isOptimal: false },
    { hour: '13:00', intensity: 420, isOptimal: false },
    { hour: '14:00', intensity: 380, isOptimal: false },
    { hour: '15:00', intensity: 350, isOptimal: true },   // High Solar
    { hour: '16:00', intensity: 340, isOptimal: true },  // High Solar
    { hour: '17:00', intensity: 480, isOptimal: false }, // Peak evening
    { hour: '18:00', intensity: 510, isOptimal: false }, // Peak evening
    { hour: '19:00', intensity: 550, isOptimal: false }, // Peak evening
    { hour: '20:00', intensity: 520, isOptimal: false },
    { hour: '21:00', intensity: 460, isOptimal: false },
    { hour: '22:00', intensity: 410, isOptimal: false },
    { hour: '23:00', intensity: 310, isOptimal: true },  // High Wind / Low Load
];

export const EvChargingOptimizer: React.FC = () => {
    const { chargingSessions, isLoading } = useFleetData();
    const [optimizationMode, setOptimizationMode] = useState<'Cost' | 'Carbon' | 'Speed'>('Carbon');

    if (isLoading) {
        return (
            <div className="w-full h-64 bg-slate-100 dark:bg-slate-800/40 rounded-2xl animate-pulse flex items-center justify-center">
                <Zap className="w-10 h-10 text-slate-300 dark:text-slate-600" />
            </div>
        );
    }

    const totalActivePower = chargingSessions.reduce((acc, session) => acc + session.currentKwDraw, 0);

    return (
        <div className="w-full bg-white dark:bg-slate-800/80 backdrop-blur-xl border border-slate-200 dark:border-slate-700/50 rounded-2xl shadow-sm overflow-hidden flex flex-col font-sans">

            {/* Header / Config Bar */}
            <div className="p-6 border-b border-slate-200 dark:border-slate-700/50 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                <div>
                    <h3 className="text-xl font-bold text-slate-800 dark:text-white flex items-center gap-2">
                        <CloudRain className="w-6 h-6 text-emerald-500" />
                        AI Grid Intensity Optimizer
                    </h3>
                    <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 max-w-xl">
                        Shifting fleet charging schedules to hours with low grid emissions intensity
                        (<span className="font-mono text-xs font-bold text-slate-600 dark:text-slate-300">gCO2/kWh</span>) reduces Scope 2 footprint substantially.
                    </p>
                </div>

                <div className="flex bg-slate-100 dark:bg-slate-900 rounded-xl p-1 shrink-0 self-start lg:self-auto">
                    {['Cost', 'Carbon', 'Speed'].map(mode => {
                        const isActive = optimizationMode === mode;
                        return (
                            <button
                                key={mode}
                                onClick={() => setOptimizationMode(mode as any)}
                                className={`
                                    px-4 py-2 text-sm font-bold rounded-lg transition-all
                                    ${isActive
                                        ? 'bg-white dark:bg-slate-800 shadow-sm text-emerald-600 dark:text-emerald-400'
                                        : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}
                                `}
                            >
                                {mode}
                            </button>
                        );
                    })}
                </div>
            </div>

            <div className="p-6 grid grid-cols-1 xl:grid-cols-3 gap-8">

                {/* Active Sessions Panel */}
                <div className="xl:col-span-1 space-y-6">
                    <div className="flex justify-between items-center">
                        <h4 className="font-bold text-slate-800 dark:text-white uppercase tracking-wider text-xs">Active Sessions</h4>
                        <span className="bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20 px-2 py-0.5 rounded-full text-xs font-bold">
                            {totalActivePower.toFixed(1)} kW Total Draw
                        </span>
                    </div>

                    <div className="space-y-3">
                        {chargingSessions.length === 0 ? (
                            <div className="p-4 border border-dashed border-slate-300 dark:border-slate-600 rounded-xl text-center text-sm font-medium text-slate-500">
                                No fleet vehicles currently charging.
                            </div>
                        ) : (
                            chargingSessions.map((chg) => (
                                <motion.div
                                    initial={{ opacity: 0, x: -10 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    key={chg.sessionId}
                                    className="p-4 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl flex items-center justify-between"
                                >
                                    <div>
                                        <div className="font-bold text-sm text-slate-800 dark:text-white">{chg.vehicleId}</div>
                                        <div className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1 mt-1">
                                            <Zap className="w-3 h-3 text-yellow-500" />
                                            {chg.currentKwDraw} kW Draw
                                        </div>
                                    </div>
                                    <div className="text-right">
                                        <div className="text-xs font-bold text-slate-600 dark:text-slate-300 font-mono">
                                            {chg.totalKwhDelivered.toFixed(1)} kWh
                                        </div>
                                        <div className="text-[10px] text-slate-400 uppercase tracking-widest mt-1">Delivered</div>
                                    </div>
                                </motion.div>
                            ))
                        )}
                    </div>

                    <button className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-emerald-500 hover:bg-emerald-600 text-white font-bold rounded-xl transition-colors shadow-lg shadow-emerald-500/20">
                        <Play className="w-4 h-4" />
                        Execute Smart Routing
                    </button>

                    <div className="p-4 bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/20 rounded-xl flex gap-3 text-sm">
                        <AlertCircle className="w-5 h-5 text-amber-500 flex-shrink-0" />
                        <div className="text-amber-800 dark:text-amber-400 leading-tight">
                            <span className="font-bold block mb-1">Peak Intensity Warning (17:00 - 19:00)</span>
                            Grid CO2 limits exceed threshold. 12 vehicles are scheduled to throttle charging speeds by 50% automatically.
                        </div>
                    </div>
                </div>

                {/* Grid Chart Panel */}
                <div className="xl:col-span-2 flex flex-col h-[400px]">
                    <div className="mb-4 flex items-center justify-between">
                        <h4 className="font-bold text-slate-800 dark:text-white flex items-center gap-2">
                            <BarChart3 className="w-4 h-4 text-slate-400" />
                            Next 12 Hours Local Grid Forecast
                        </h4>
                        <button className="p-2 text-slate-400 hover:text-slate-600 bg-slate-50 hover:bg-slate-100 rounded-lg transition-colors">
                            <Settings className="w-4 h-4" />
                        </button>
                    </div>

                    {/* Highly bespoke CSS-based Bar Chart for maximum speed & stability without Recharts dependency here */}
                    <div className="flex-1 w-full flex items-end gap-2 sm:gap-4 relative pt-10 pb-6 border-b border-l border-slate-200 dark:border-slate-700">

                        {/* Y-Axis Labeling */}
                        <div className="absolute left-[-35px] top-0 bottom-0 w-[30px] flex flex-col justify-between items-end pb-6 pt-10 text-[10px] font-mono text-slate-400 font-bold">
                            <span>600</span>
                            <span>400</span>
                            <span>200</span>
                            <span>0</span>
                        </div>

                        {/* Chart Bars */}
                        {intensityForecast.map((hourObj, idx) => {
                            const barHeightPct = (hourObj.intensity / 600) * 100;
                            const isOpt = hourObj.isOptimal && optimizationMode === 'Carbon';

                            return (
                                <div key={idx} className="flex-1 flex flex-col items-center justify-end h-full relative group cursor-pointer">
                                    <motion.div
                                        initial={{ height: '0%' }}
                                        animate={{ height: `${barHeightPct}%` }}
                                        transition={{ duration: 0.8, delay: idx * 0.05, type: 'spring', stiffness: 200, damping: 20 }}
                                        className={`w-full rounded-t-lg transition-colors relative
                                            ${isOpt ? 'bg-emerald-500' : 'bg-slate-300 dark:bg-slate-600'}
                                            group-hover:opacity-80
                                        `}
                                    >
                                        <div className="absolute -top-8 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity bg-slate-800 text-white text-[10px] py-1 px-2 rounded font-mono font-bold pointer-events-none z-10 whitespace-nowrap">
                                            {hourObj.intensity} gCO2
                                        </div>
                                    </motion.div>
                                    <div className="absolute -bottom-6 text-[10px] font-bold text-slate-400 rotate-45 transform origin-top-left ml-3">
                                        {hourObj.hour}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>

            </div>
        </div>
    );
};

export default EvChargingOptimizer;
