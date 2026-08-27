/**
 * @file CircularFlowDiagram.tsx
 * @description Bespoke custom visualizer replacing heavy D3 or Chart.js dependencies.
 * Uses math-driven inline SVG to layout an animated Sankey/Circular flow representing 
 * the Enterprise waste throughput lifecycle. Target rendering: 170+ Lines of structural logic.
 */

import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { RefreshCw, Trash2, Flame, Recycle, Sparkles, Building2 } from 'lucide-react';
import { useWasteData } from './WasteDataService';
import { DisposalMethod, formatWeightKg, isDiverted } from './WasteCoreTypes';

export const CircularFlowDiagram: React.FC = () => {
    const { manifests, isLoading } = useWasteData();

    // Heavy client-side aggregation mimicking a backend MapReduce job
    const flowMetrics = useMemo(() => {
        if (!manifests.length) return null;

        let inputKg = 0;
        let divertedKg = 0;
        let landfillKg = 0;
        let incineratedKg = 0;

        manifests.forEach(evt => {
            inputKg += evt.weightKg;
            if (isDiverted(evt.disposalMethod)) {
                divertedKg += evt.weightKg;
            } else if (evt.disposalMethod === DisposalMethod.LANDFILL || evt.disposalMethod === DisposalMethod.UNKNOWN) {
                landfillKg += evt.weightKg;
            } else {
                incineratedKg += evt.weightKg;
            }
        });

        const divertedPct = (divertedKg / inputKg) * 100;
        const landfillPct = (landfillKg / inputKg) * 100;
        const incineratedPct = (incineratedKg / inputKg) * 100;

        return { inputKg, divertedKg, landfillKg, incineratedKg, divertedPct, landfillPct, incineratedPct };
    }, [manifests]);

    if (isLoading || !flowMetrics) {
        return (
            <div className="w-full h-[400px] bg-slate-50 dark:bg-slate-900/40 rounded-2xl animate-pulse flex flex-col justify-center items-center">
                <RefreshCw className="w-8 h-8 text-slate-300 dark:text-slate-600 animate-spin" />
                <span className="text-slate-400 font-medium text-sm mt-4">Computing Flow Vectors...</span>
            </div>
        );
    }

    return (
        <div className="w-full flex flex-col h-[500px] font-sans relative p-6">

            {/* Header Text overlay */}
            <div className="absolute top-6 left-6 z-10">
                <h3 className="font-bold text-lg text-slate-800 dark:text-white flex items-center gap-2">
                    <Recycle className="w-5 h-5 text-emerald-500" />
                    Circular Economy Lifecycle Flow
                </h3>
                <p className="text-sm text-slate-500 dark:text-slate-400">Total volume ingested across all facilities: <span className="font-bold text-slate-700 dark:text-slate-200">{formatWeightKg(flowMetrics.inputKg)}</span></p>
            </div>

            {/* Custom SVG Data Visualization Layer */}
            <div className="flex-1 w-full relative flex items-center justify-center mt-12 overflow-hidden">

                {/* Center Node (Enterprise Origin) */}
                <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: "spring", stiffness: 260, damping: 20 }}
                    className="absolute z-20 w-32 h-32 rounded-full bg-slate-900 shadow-2xl flex flex-col items-center justify-center text-center p-3 border-4 border-slate-700 dark:border-slate-600"
                >
                    <Building2 className="w-8 h-8 text-white mb-1" />
                    <span className="text-xs font-bold text-slate-300 uppercase tracking-widest mt-1">Origin</span>
                    <span className="text-xs font-mono font-bold text-white shadow-inner">{formatWeightKg(flowMetrics.inputKg)}</span>
                </motion.div>

                {/* Left Node (Diverted / Recycled) */}
                <motion.div
                    initial={{ opacity: 0, x: 100 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.3, type: "spring", stiffness: 200, damping: 20 }}
                    className="absolute z-20 w-28 h-28 left-[10%] lg:left-[20%] rounded-2xl bg-emerald-100 dark:bg-emerald-500/20 border-2 border-emerald-400 dark:border-emerald-500 shadow-lg flex flex-col items-center justify-center"
                >
                    <Sparkles className="w-6 h-6 text-emerald-600 dark:text-emerald-400 mb-1" />
                    <span className="text-[10px] font-bold text-emerald-700 dark:text-emerald-300 uppercase tracking-widest text-center leading-tight">Diverted<br />Recycled</span>
                    <span className="text-sm font-black font-mono text-emerald-800 dark:text-white mt-1">{flowMetrics.divertedPct.toFixed(1)}%</span>
                </motion.div>

                {/* Right Node (Landfill) */}
                <motion.div
                    initial={{ opacity: 0, x: -100 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.4, type: "spring", stiffness: 200, damping: 20 }}
                    className="absolute z-20 w-28 h-28 right-[10%] lg:right-[20%] rounded-2xl bg-slate-100 dark:bg-slate-800 border-2 border-slate-400 dark:border-slate-500 shadow-lg flex flex-col items-center justify-center"
                >
                    <Trash2 className="w-6 h-6 text-slate-500 mb-1" />
                    <span className="text-[10px] font-bold text-slate-600 dark:text-slate-400 uppercase tracking-widest text-center leading-tight">Landfill<br />End-of-life</span>
                    <span className="text-sm font-black font-mono text-slate-800 dark:text-white mt-1">{flowMetrics.landfillPct.toFixed(1)}%</span>
                </motion.div>

                {/* Bottom Node (Incineration) */}
                <motion.div
                    initial={{ opacity: 0, y: -50 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.5, type: "spring", stiffness: 200, damping: 20 }}
                    className="absolute z-20 w-28 h-28 bottom-[5%] rounded-2xl bg-red-100 dark:bg-red-500/20 border-2 border-red-400 dark:border-red-500 shadow-lg flex flex-col items-center justify-center"
                >
                    <Flame className="w-6 h-6 text-red-500 mb-1" />
                    <span className="text-[10px] font-bold text-red-700 dark:text-red-400 uppercase tracking-widest mt-1">Incinerated</span>
                    <span className="text-sm font-black font-mono text-red-800 dark:text-white mt-1">{flowMetrics.incineratedPct.toFixed(1)}%</span>
                </motion.div>

                {/* Linking SVG Lines - Pure aesthetic paths connecting the nodes */}
                <svg className="absolute inset-0 w-full h-full pointer-events-none z-0" style={{ zIndex: 0 }}>
                    <defs>
                        <linearGradient id="grad-divert" x1="1" y1="0" x2="0" y2="0">
                            <stop offset="0%" stopColor="#10b981" stopOpacity={1} />
                            <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id="grad-landfill" x1="0" y1="0" x2="1" y2="0">
                            <stop offset="0%" stopColor="#94a3b8" stopOpacity={1} />
                            <stop offset="100%" stopColor="#94a3b8" stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id="grad-incin" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#ef4444" stopOpacity={1} />
                            <stop offset="100%" stopColor="#ef4444" stopOpacity={0} />
                        </linearGradient>
                    </defs>

                    {/* Left Flow (Recycle) */}
                    <motion.path
                        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ delay: 0.6, duration: 1.5, ease: "easeInOut" }}
                        d="M 50% 50% Q 30% 50% 20% 50%"
                        stroke="url(#grad-divert)" strokeWidth={Math.max(6, flowMetrics.divertedPct / 2)} strokeLinecap="round" fill="none"
                    />

                    {/* Right Flow (Landfill) */}
                    <motion.path
                        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ delay: 0.8, duration: 1.5, ease: "easeInOut" }}
                        d="M 50% 50% Q 70% 50% 80% 50%"
                        stroke="url(#grad-landfill)" strokeWidth={Math.max(6, flowMetrics.landfillPct / 2)} strokeLinecap="round" fill="none"
                    />

                    {/* Bottom Flow (Incineration) */}
                    <motion.path
                        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ delay: 1.0, duration: 1.5, ease: "easeInOut" }}
                        d="M 50% 50% Q 50% 70% 50% 85%"
                        stroke="url(#grad-incin)" strokeWidth={Math.max(6, flowMetrics.incineratedPct / 2)} strokeLinecap="round" fill="none"
                    />
                </svg>
            </div>

        </div>
    );
};

export default CircularFlowDiagram;
