/**
 * @file VehicleStatusTable.tsx
 * @description Master paginated reporting table parsing the robust Vehicle telemetry data layer
 */

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Search, Filter, ChevronLeft, ChevronRight,
    MoreVertical, Navigation, Battery, Fuel, Wrench, ShieldAlert
} from 'lucide-react';
import { useFleetData } from './FleetDataService';
import { getStatusColorClasses, formatPingTime, isZeroEmission, VehicleStatus, PowertrainType } from './FleetCoreTypes';

export const VehicleStatusTable: React.FC = () => {
    const { fleet, isLoading } = useFleetData();
    const [search, setSearch] = useState('');
    const [statusFilter, setStatusFilter] = useState<string>('ALL');

    if (isLoading) {
        return (
            <div className="w-full bg-white dark:bg-slate-800/80 rounded-2xl h-96 flex items-center justify-center">
                <SpinnerPlaceholder />
            </div>
        );
    }

    const filteredFleet = fleet
        .filter(v => v.licensePlate.toLowerCase().includes(search.toLowerCase()) || v.vehicleId.toLowerCase().includes(search.toLowerCase()))
        .filter(v => statusFilter === 'ALL' || v.status === statusFilter);

    // Mock Pagination Constants
    const totalEntries = filteredFleet.length;
    const pageLength = 5;

    return (
        <div className="w-full bg-white dark:bg-slate-800/80 backdrop-blur-xl border border-slate-200 dark:border-slate-700/50 rounded-2xl shadow-sm overflow-hidden flex flex-col h-full font-sans">

            {/* Table Control Header */}
            <div className="p-5 border-b border-slate-200 dark:border-slate-700/50 flex flex-col md:flex-row justify-between md:items-center gap-4 bg-slate-50/50 dark:bg-slate-900/20">
                <div>
                    <h3 className="text-lg font-bold text-slate-800 dark:text-white">Active Fleet Telemetry Stream</h3>
                    <p className="text-xs font-medium text-slate-500 mt-1">Live data ingested from enterprise vehicular IoT endpoints.</p>
                </div>

                <div className="flex flex-col sm:flex-row items-center gap-3 w-full md:w-auto">
                    <div className="relative w-full sm:w-64">
                        <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
                        <input
                            type="text"
                            placeholder="Find ID or License..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-xl pl-9 pr-3 py-2 w-full text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none dark:text-white"
                        />
                    </div>
                    <div className="relative w-full sm:w-48">
                        <select
                            value={statusFilter}
                            onChange={(e) => setStatusFilter(e.target.value)}
                            className="bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-xl pl-3 pr-8 py-2 w-full text-sm font-medium focus:ring-2 focus:ring-emerald-500 focus:outline-none appearance-none cursor-pointer dark:text-white"
                        >
                            <option value="ALL">All Statuses</option>
                            <option value={VehicleStatus.ACTIVE_EN_ROUTE}>En Route</option>
                            <option value={VehicleStatus.CHARGING_STATION}>Charging</option>
                            <option value={VehicleStatus.MAINTENANCE_REQUIRED}>Maintenance</option>
                            <option value={VehicleStatus.IDLE}>Idle</option>
                        </select>
                        <Filter className="absolute right-3 top-2.5 w-4 h-4 text-slate-400 pointer-events-none" />
                    </div>
                </div>
            </div>

            {/* Table Core Content */}
            <div className="overflow-x-auto w-full flex-1">
                <table className="w-full min-w-[800px] text-left border-collapse">
                    <thead className="bg-slate-100 dark:bg-slate-800/80 sticky top-0 z-10">
                        <tr>
                            <th className="px-6 py-4 font-bold text-xs uppercase tracking-wider text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-700">Vehicle Profile</th>
                            <th className="px-6 py-4 font-bold text-xs uppercase tracking-wider text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-700">Status & Last Ping</th>
                            <th className="px-6 py-4 font-bold text-xs uppercase tracking-wider text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-700">Energy & Powertrain</th>
                            <th className="px-6 py-4 font-bold text-xs uppercase tracking-wider text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-700">Emissions Avg</th>
                            <th className="px-6 py-4 border-b border-slate-200 dark:border-slate-700"></th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-700/50">
                        <AnimatePresence>
                            {filteredFleet.length > 0 ? (
                                filteredFleet.slice(0, pageLength).map((veh, i) => (
                                    <motion.tr
                                        initial={{ opacity: 0, y: 15 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        exit={{ opacity: 0, scale: 0.98 }}
                                        transition={{ delay: i * 0.05 }}
                                        key={veh.vehicleId}
                                        className="hover:bg-slate-50 dark:hover:bg-slate-800/60 transition-colors group"
                                    >
                                        <td className="px-6 py-4 align-top">
                                            <div className="flex flex-col">
                                                <span className="font-extrabold text-slate-800 dark:text-white group-hover:text-emerald-600 transition-colors">
                                                    {veh.licensePlate}
                                                </span>
                                                <span className="text-xs text-slate-500 dark:text-slate-400 font-mono mt-0.5">
                                                    ID: {veh.vehicleId}
                                                </span>
                                                <span className="text-xs text-slate-400 mt-2 flex items-center">
                                                    {veh.year} {veh.make} {veh.model}
                                                </span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 align-top">
                                            <div className="flex flex-col items-start gap-2">
                                                <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold border leading-none ${getStatusColorClasses(veh.status)}`}>
                                                    {veh.status === VehicleStatus.MAINTENANCE_REQUIRED && <Wrench className="w-3 h-3 mr-1" />}
                                                    {veh.status}
                                                </span>
                                                <span className="text-xs font-mono font-medium text-slate-500 flex items-center mt-1">
                                                    <Navigation className="w-3 h-3 mr-1.5 text-slate-400" />
                                                    {formatPingTime(veh.telemetry.lastPingTimestamp)}
                                                </span>
                                                {veh.maintenanceAlerts.length > 0 && (
                                                    <div className="text-[10px] text-red-500 flex items-center mt-1 font-bold">
                                                        <ShieldAlert className="w-3 h-3 mr-1" />
                                                        {veh.maintenanceAlerts.length} Critical Alert(s)
                                                    </div>
                                                )}
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 align-top">
                                            <div className="flex flex-col gap-2">
                                                <span className={`text-xs font-bold px-2 py-0.5 rounded
                                                    ${isZeroEmission(veh.powertrain) ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-500/20 dark:text-emerald-300' : 'bg-slate-200 text-slate-800 dark:bg-slate-700 dark:text-slate-300'}
                                                `}>
                                                    {veh.powertrain}
                                                </span>
                                                <div className="flex gap-4 mt-2">
                                                    {veh.telemetry.batteryLevelPct !== null && (
                                                        <div className="flex flex-col items-start">
                                                            <div className="flex items-center text-xs font-bold text-slate-600 dark:text-slate-400 mb-1">
                                                                <Battery className="w-4 h-4 mr-1 text-emerald-500" /> SoC
                                                            </div>
                                                            <div className="w-16 h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                                                                <div className={`h-full ${veh.telemetry.batteryLevelPct > 20 ? 'bg-emerald-500' : 'bg-red-500'}`} style={{ width: `${veh.telemetry.batteryLevelPct}%` }}></div>
                                                            </div>
                                                            <p className="text-[10px] font-mono font-bold mt-0.5">{veh.telemetry.batteryLevelPct}%</p>
                                                        </div>
                                                    )}
                                                    {veh.telemetry.fuelLevelPct !== null && (
                                                        <div className="flex flex-col items-start">
                                                            <div className="flex items-center text-xs font-bold text-slate-600 dark:text-slate-400 mb-1">
                                                                <Fuel className="w-4 h-4 mr-1 text-amber-500" /> Fuel
                                                            </div>
                                                            <div className="w-16 h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                                                                <div className="h-full bg-amber-500" style={{ width: `${veh.telemetry.fuelLevelPct}%` }}></div>
                                                            </div>
                                                            <p className="text-[10px] font-mono font-bold mt-0.5">{veh.telemetry.fuelLevelPct}%</p>
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 align-top">
                                            <div className="text-2xl font-black text-slate-800 dark:text-white tracking-tighter">
                                                {veh.averageDailyEmissions.toFixed(1)} <span className="text-xs text-slate-500 font-sans tracking-normal font-semibold">tCO2e</span>
                                            </div>
                                            <div className="text-[10px] font-bold text-slate-400 uppercase mt-2">
                                                {veh.telemetry.estimatedRangeMiles} mi Est. Range
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 align-middle text-right">
                                            <button className="p-2 text-slate-400 hover:text-emerald-600 bg-transparent hover:bg-emerald-50 dark:hover:bg-emerald-500/10 rounded-lg transition-colors outline-none cursor-pointer">
                                                <MoreVertical className="w-5 h-5" />
                                            </button>
                                        </td>
                                    </motion.tr>
                                ))
                            ) : (
                                <tr>
                                    <td colSpan={5} className="px-6 py-16 text-center text-slate-500 font-medium">
                                        No fleet vehicles resolved for this search matrix.
                                    </td>
                                </tr>
                            )}
                        </AnimatePresence>
                    </tbody>
                </table>
            </div>

            {/* Pagination Controls */}
            <div className="px-6 py-4 border-t border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-900/20 flex flex-col sm:flex-row items-center justify-between text-sm">
                <span className="text-slate-500 font-medium mb-3 sm:mb-0">
                    Showing <span className="font-bold text-slate-800 dark:text-white">{Math.min(totalEntries, pageLength)}</span> of {totalEntries} Vehicles
                </span>
                <div className="flex gap-2">
                    <button className="flex items-center gap-1 px-3 py-1.5 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-50 disabled:opacity-50 transition-colors">
                        <ChevronLeft className="w-4 h-4" /> Prev
                    </button>
                    <button className="flex items-center gap-1 px-3 py-1.5 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-50 transition-colors">
                        Next <ChevronRight className="w-4 h-4" />
                    </button>
                </div>
            </div>

        </div>
    );
};

const SpinnerPlaceholder = () => (
    <div className="flex flex-col items-center p-8">
        <div className="w-8 h-8 rounded-full border-4 border-emerald-200 border-t-emerald-500 animate-spin mb-4"></div>
        <span className="text-slate-400 font-medium animate-pulse">Syncing Telemetry...</span>
    </div>
);

export default VehicleStatusTable;
