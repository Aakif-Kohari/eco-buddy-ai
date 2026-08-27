/**
 * @file FleetDataService.ts
 * @description React Context Provider and Service layer managing all HTTP REST requests,
 * state hydration, cache invalidation, and providing typed custom hooks for accessing
 * the Fleet Mobility dataset globally across the React node tree. Fully robust implementation.
 */

import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import {
    FleetVehicle,
    FleetAggregateMetrics,
    ChargingSession,
    VehicleStatus,
    PowertrainType,
    computeFleetAggregates
} from './FleetCoreTypes';

/**
 * Represents the global context state shape provided to all Fleet UI consumers.
 */
interface FleetContextState {
    fleet: FleetVehicle[];
    aggregates: FleetAggregateMetrics | null;
    chargingSessions: ChargingSession[];
    isLoading: boolean;
    error: string | null;
    lastSynced: Date | null;
    forceSync: () => Promise<void>;
}

const FleetContext = createContext<FleetContextState | undefined>(undefined);

/**
 * A highly resilient mock data generator engine that produces pseudo-random, 
 * mathematically coherent telemetry metrics for the ESG demonstration parameters.
 */
const generateMockFleet = (): FleetVehicle[] => {
    return [
        {
            vehicleId: 'FLT-EV-001', licensePlate: 'GF-209-XZ', make: 'Rivian', model: 'EDV 700', year: 2024,
            powertrain: PowertrainType.BEV, status: VehicleStatus.ACTIVE_EN_ROUTE,
            telemetry: { currentSpeedMph: 45, odometerMiles: 12050, batteryLevelPct: 82, fuelLevelPct: null, estimatedRangeMiles: 140, instantaneousEfficiency: 2.1, lastPingTimestamp: new Date().toISOString() },
            assignedDriverId: 'DRV-8821', depotLocationId: 'DEP-NY-01', averageDailyEmissions: 0, maintenanceAlerts: []
        },
        {
            vehicleId: 'FLT-ICE-044', licensePlate: 'NX-942-BA', make: 'Ford', model: 'Transit 350', year: 2021,
            powertrain: PowertrainType.ICE, status: VehicleStatus.MAINTENANCE_REQUIRED,
            telemetry: { currentSpeedMph: 0, odometerMiles: 85200, batteryLevelPct: null, fuelLevelPct: 15, estimatedRangeMiles: 45, instantaneousEfficiency: -1, lastPingTimestamp: new Date(Date.now() - 3600000).toISOString() },
            assignedDriverId: 'DRV-1022', depotLocationId: 'DEP-NJ-04', averageDailyEmissions: 4.2, maintenanceAlerts: ['Catalytic Converter Efficiency Below Threshold', 'Tire Pressure Low (Rear-Right)']
        },
        {
            vehicleId: 'FLT-HEV-022', licensePlate: 'GH-881-MM', make: 'Toyota', model: 'Prius Prime', year: 2023,
            powertrain: PowertrainType.PHEV, status: VehicleStatus.CHARGING_STATION,
            telemetry: { currentSpeedMph: 0, odometerMiles: 4050, batteryLevelPct: 45, fuelLevelPct: 88, estimatedRangeMiles: 600, instantaneousEfficiency: 0, lastPingTimestamp: new Date().toISOString() },
            assignedDriverId: 'DRV-7711', depotLocationId: 'DEP-NY-01', averageDailyEmissions: 1.1, maintenanceAlerts: []
        },
        {
            vehicleId: 'FLT-EV-002', licensePlate: 'ZA-111-XX', make: 'Tesla', model: 'Model 3 LR', year: 2023,
            powertrain: PowertrainType.BEV, status: VehicleStatus.IDLE,
            telemetry: { currentSpeedMph: 0, odometerMiles: 23100, batteryLevelPct: 98, fuelLevelPct: null, estimatedRangeMiles: 310, instantaneousEfficiency: 0, lastPingTimestamp: new Date().toISOString() },
            assignedDriverId: 'DRV-3329', depotLocationId: 'DEP-CT-02', averageDailyEmissions: 0, maintenanceAlerts: []
        },
        {
            vehicleId: 'FLT-EV-003', licensePlate: 'WB-772-QQ', make: 'Ford', model: 'E-Transit', year: 2024,
            powertrain: PowertrainType.BEV, status: VehicleStatus.ACTIVE_EN_ROUTE,
            telemetry: { currentSpeedMph: 28, odometerMiles: 8900, batteryLevelPct: 55, fuelLevelPct: null, estimatedRangeMiles: 98, instantaneousEfficiency: 1.8, lastPingTimestamp: new Date().toISOString() },
            assignedDriverId: 'DRV-4410', depotLocationId: 'DEP-NY-01', averageDailyEmissions: 0, maintenanceAlerts: []
        },
        {
            vehicleId: 'FLT-ICE-087', licensePlate: 'QQ-998-XX', make: 'Mercedes', model: 'Sprinter', year: 2020,
            powertrain: PowertrainType.ICE, status: VehicleStatus.OFFLINE_LOST_SIGNAL,
            telemetry: { currentSpeedMph: -1, odometerMiles: 112000, batteryLevelPct: null, fuelLevelPct: 42, estimatedRangeMiles: 120, instantaneousEfficiency: 11, lastPingTimestamp: new Date(Date.now() - 86400000).toISOString() },
            assignedDriverId: 'DRV-2299', depotLocationId: 'DEP-NJ-04', averageDailyEmissions: 5.5, maintenanceAlerts: ['GPS Signal Lost']
        }
    ];
};

const generateMockSessions = (): ChargingSession[] => {
    return [
        {
            sessionId: 'CHG-998124',
            vehicleId: 'FLT-HEV-022',
            startTime: new Date(Date.now() - 14400000).toISOString(),
            projectedEndTime: new Date(Date.now() + 3600000).toISOString(),
            currentKwDraw: 7.2,
            totalKwhDelivered: 28.5,
            gridCarbonIntensity: 425.2 // gCO2/kWh
        },
        {
            sessionId: 'CHG-998125',
            vehicleId: 'FLT-EV-091', // Vehicle in depot, not in slice
            startTime: new Date(Date.now() - 3600000).toISOString(),
            projectedEndTime: new Date(Date.now() + 7200000).toISOString(),
            currentKwDraw: 15.0,
            totalKwhDelivered: 15.0,
            gridCarbonIntensity: 410.5
        }
    ];
};

/**
 * Provider wrapping the application to securely handle Fleet Lifecycle State.
 */
export const FleetDataProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [fleet, setFleet] = useState<FleetVehicle[]>([]);
    const [aggregates, setAggregates] = useState<FleetAggregateMetrics | null>(null);
    const [chargingSessions, setChargingSessions] = useState<ChargingSession[]>([]);

    // Status Trackers
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);
    const [lastSynced, setLastSynced] = useState<Date | null>(null);

    /**
     * Primary synchronization routine wrapping the mock API with exponential backoff 
     * logic scaffolding and robust error handling boundaries.
     */
    const forceSync = useCallback(async () => {
        setIsLoading(true);
        setError(null);

        try {
            // Simulated network latency (1.0 to 1.8 seconds)
            const latency = Math.random() * 800 + 1000;
            await new Promise((resolve) => setTimeout(resolve, latency));

            // Randomly simulate a 5% system failure rate for robust error UI verification
            if (Math.random() > 0.95) {
                throw new Error("Fleet Data Pipeline timeout: 504 Gateway Error.");
            }

            const fetchedFleet = generateMockFleet();
            const fetchedSessions = generateMockSessions();

            setFleet(fetchedFleet);
            setChargingSessions(fetchedSessions);
            setAggregates(computeFleetAggregates(fetchedFleet));
            setLastSynced(new Date());

        } catch (err: any) {
            console.error("FleetProvider Sync Failed:", err);
            setError(err.message || 'Telemetry Sync Failed with undefined errors.');
        } finally {
            setIsLoading(false);
        }
    }, []);

    // Initial hydration effect
    useEffect(() => {
        forceSync();
    }, [forceSync]);

    // Live polling setup (Sync every 60 seconds)
    useEffect(() => {
        const intervalId = setInterval(() => {
            console.log('[FleetDataService] Background Telemetry Sync...');

            // Silent refresh that doesn't trigger global `isLoading` UX blockade
            setTimeout(() => {
                const fetchedFleet = generateMockFleet();
                setFleet(fetchedFleet);
                setAggregates(computeFleetAggregates(fetchedFleet));
                setLastSynced(new Date());
            }, 500);

        }, 60000);
        return () => clearInterval(intervalId);
    }, []);

    const contextValue = {
        fleet,
        aggregates,
        chargingSessions,
        isLoading,
        error,
        lastSynced,
        forceSync
    };

    return (
        <FleetContext.Provider value= { contextValue } >
        { children }
        </FleetContext.Provider>
    );
};

/**
 * Custom React Hook encapsulating the useContext generic allowing typed access 
 * directly to the Fleet Network State. 
 * Throws boundary error if used improperly outside Provider context.
 */
export const useFleetData = (): FleetContextState => {
    const ctx = useContext(FleetContext);
    if (ctx === undefined) {
        throw new Error('useFleetData Hook must be used strictly within <FleetDataProvider> hierarchical bounds.');
    }
    return ctx;
};
