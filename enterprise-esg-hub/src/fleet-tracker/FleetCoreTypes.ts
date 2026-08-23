/**
 * @file FleetCoreTypes.ts
 * @description Core TypeScript interfaces, strict enums, and utility helper functions 
 * required to drive the architecture of the Enterprise Green Mobility Fleet Tracker.
 * These types enforce strict type-safety across the entire Fleet Tracking module,
 * validating all incoming telemetry data and bounding the state capabilities 
 * of the interactive React frontend components.
 */

/**
 * Valid states a Fleet Vehicle can be continuously emitting 
 * via its IoT Telemetry stream.
 */
export enum VehicleStatus {
    ACTIVE_EN_ROUTE = 'Active (En Route)',
    CHARGING_STATION = 'Charging Station',
    MAINTENANCE_REQUIRED = 'Maintenance Required',
    IDLE = 'Idle (Depot)',
    OFFLINE_LOST_SIGNAL = 'Offline / Lost Signal',
}

/**
 * Powertrain categorizations used to calculate carbon intensity and
 * evaluate progress toward 2030 corporate sustainability goals.
 */
export enum PowertrainType {
    BEV = 'Battery Electric (BEV)',
    PHEV = 'Plugin Hybrid (PHEV)',
    HEV = 'Hybrid Electric (HEV)',
    ICE = 'Internal Combustion (ICE)',
    FCEV = 'Hydrogen Fuel Cell (FCEV)'
}

/**
 * Standard Telemetry footprint expected from each connected vehicle.
 */
export interface TelemetryData {
    currentSpeedMph: number;
    odometerMiles: number;
    batteryLevelPct: number | null; // Nullable for ICE vehicles
    fuelLevelPct: number | null;    // Nullable for EV vehicles
    estimatedRangeMiles: number;
    instantaneousEfficiency: number; // in kWh/mi or mpg depending on powertrain
    lastPingTimestamp: string;
}

/**
 * Complex interface defining the complete representation of an Enterprise Fleet Vehicle.
 */
export interface FleetVehicle {
    vehicleId: string;
    licensePlate: string;
    make: string;
    model: string;
    year: number;
    powertrain: PowertrainType;
    status: VehicleStatus;
    telemetry: TelemetryData;
    assignedDriverId: string;
    depotLocationId: string;
    averageDailyEmissions: number; // tCO2e
    maintenanceAlerts: string[];
}

/**
 * Rollup aggregation metrics for the entire regional footprint.
 */
export interface FleetAggregateMetrics {
    totalVehicles: number;
    zeroEmissionVehicles: number;
    totalDailyDistanceMiles: number;
    fleetWideEfficiencyScore: number;
    dailyCarbonEmissions: number; // in tCO2e
    activeChargingCount: number;
    criticalAlertsTotal: number;
}

/**
 * EV charging spot structure used by the Scheduling Optimizer.
 */
export interface ChargingSession {
    sessionId: string;
    vehicleId: string;
    startTime: string;
    projectedEndTime: string;
    currentKwDraw: number;
    totalKwhDelivered: number;
    gridCarbonIntensity: number; // gCO2/kWh at time of charge
}

/**
 * UTILITIES
 */

/**
 * Generates Tailwind CSS class string based on the status of a vehicle.
 * @param status The current operational status of the vehicle.
 * @returns React compatible className string.
 */
export const getStatusColorClasses = (status: VehicleStatus): string => {
    switch (status) {
        case VehicleStatus.ACTIVE_EN_ROUTE:
            return 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20';
        case VehicleStatus.CHARGING_STATION:
            return 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20';
        case VehicleStatus.MAINTENANCE_REQUIRED:
            return 'bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20';
        case VehicleStatus.IDLE:
            return 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20';
        case VehicleStatus.OFFLINE_LOST_SIGNAL:
            return 'bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-500/20';
        default:
            return 'bg-slate-100 text-slate-500 border-slate-200';
    }
};

/**
 * Checks if a given powertrain is generally considered Zero Emission (ZEV).
 * This relies on California CARB definitions (BEV and FCEV constitute true ZEV).
 * @param pt The powertrain type enum.
 * @returns boolean determining emission status.
 */
export const isZeroEmission = (pt: PowertrainType): boolean => {
    return pt === PowertrainType.BEV || pt === PowertrainType.FCEV;
};

/**
 * Helper to pretty-format dates for the Telemetry Table UI.
 * @param isoString An ISO formatted date string.
 * @returns Human readable time string.
 */
export const formatPingTime = (isoString: string): string => {
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return "Unknown Last Ping";

    // Formatting as e.g. "Today at 2:34 PM" if today, otherwise Standard Short Date
    const today = new Date();
    const isToday = date.getDate() === today.getDate() &&
        date.getMonth() === today.getMonth() &&
        date.getFullYear() === today.getFullYear();

    const timeFormatter = new Intl.DateTimeFormat('en-US', { hour: 'numeric', minute: 'numeric' });

    if (isToday) {
        return `Today at ${timeFormatter.format(date)}`;
    }

    const dateFormatter = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: 'numeric' });
    return dateFormatter.format(date);
};

/**
 * Calculates raw aggregates required by the FleetDashboard metrics engine.
 * Takes the heavy O(N) iteration out of the React render cycle.
 * @param fleet The full fleet slice of nodes.
 * @returns Aggregate Fleet Metrics object.
 */
export const computeFleetAggregates = (fleet: FleetVehicle[]): FleetAggregateMetrics => {
    if (!fleet || fleet.length === 0) {
        return {
            totalVehicles: 0,
            zeroEmissionVehicles: 0,
            totalDailyDistanceMiles: 0,
            fleetWideEfficiencyScore: 0,
            dailyCarbonEmissions: 0,
            activeChargingCount: 0,
            criticalAlertsTotal: 0
        };
    }

    let zevCount = 0;
    let distanceSum = 0;
    let emissionsSum = 0;
    let chargingCount = 0;
    let alertsCount = 0;

    for (const v of fleet) {
        if (isZeroEmission(v.powertrain)) zevCount++;
        distanceSum += (v.telemetry?.odometerMiles || 0); // Mock summing all distance? Just a proxy in this mock.
        emissionsSum += v.averageDailyEmissions;

        if (v.status === VehicleStatus.CHARGING_STATION) chargingCount++;
        if (v.maintenanceAlerts.length > 0) alertsCount += v.maintenanceAlerts.length;
    }

    return {
        totalVehicles: fleet.length,
        zeroEmissionVehicles: zevCount,
        totalDailyDistanceMiles: distanceSum,
        fleetWideEfficiencyScore: 88, // Constant for mock simplicity
        dailyCarbonEmissions: emissionsSum,
        activeChargingCount: chargingCount,
        criticalAlertsTotal: alertsCount
    };
};
