/**
 * @file WasteDataService.ts
 * @description Injects global state configuration into the React Tree, supplying mock
 * databases and API hydration patterns for resolving Waste telemetry metrics. 
 */

import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import {
    WasteCategory,
    DisposalMethod,
    WasteManifestEvent,
    FacilityWasteMetrics,
    EnterpriseCircularMetrics,
    compileEnterpriseMetrics
} from './WasteCoreTypes';

/**
 * Service Context Outline
 */
interface WasteContextState {
    manifests: WasteManifestEvent[];
    facilities: FacilityWasteMetrics[];
    enterpriseStats: EnterpriseCircularMetrics | null;
    isLoading: boolean;
    error: string | null;
    refreshData: () => Promise<void>;
}

const WasteContext = createContext<WasteContextState | undefined>(undefined);

/**
 * Simulates heavy backend persistence data modeling.
 */
const generateMockWasteManifests = (): WasteManifestEvent[] => {
    return [
        { manifestId: 'WM-811A', timestamp: '2024-04-12T08:30:00Z', originFacilityId: 'FAC-HQ01', category: WasteCategory.PAPER_CARDBOARD, weightKg: 1250, destinationProvider: 'EcoRecycle Partners', disposalMethod: DisposalMethod.RECYCLED, certified: true, costUsd: 150 },
        { manifestId: 'WM-811B', timestamp: '2024-04-12T09:15:00Z', originFacilityId: 'FAC-HQ01', category: WasteCategory.ORGANIC, weightKg: 840, destinationProvider: 'City Compost Services', disposalMethod: DisposalMethod.COMPOSTED, certified: true, costUsd: 220 },
        { manifestId: 'WM-809F', timestamp: '2024-04-10T14:45:00Z', originFacilityId: 'FAC-MN02', category: WasteCategory.E_WASTE, weightKg: 315, destinationProvider: 'Silicon Loop Recovery', disposalMethod: DisposalMethod.UPCYCLED, certified: true, costUsd: 450 },
        { manifestId: 'WM-802C', timestamp: '2024-04-05T11:20:00Z', originFacilityId: 'FAC-TX09', category: WasteCategory.MIXED_SOLID, weightKg: 4200, destinationProvider: 'WasteMgmt Inc', disposalMethod: DisposalMethod.LANDFILL, certified: false, costUsd: 850 },
        { manifestId: 'WM-799E', timestamp: '2024-04-01T16:00:00Z', originFacilityId: 'FAC-MN02', category: WasteCategory.HAZARDOUS, weightKg: 110, destinationProvider: 'ChemSafe Disposal', disposalMethod: DisposalMethod.INCINERATED_FLARED, certified: true, costUsd: 1200 },
        { manifestId: 'WM-795A', timestamp: '2024-03-28T10:10:00Z', originFacilityId: 'FAC-TX09', category: WasteCategory.PLASTIC, weightKg: 950, destinationProvider: 'OceanBlue Recovery', disposalMethod: DisposalMethod.RECYCLED, certified: true, costUsd: 310 },
        { manifestId: 'WM-782Z', timestamp: '2024-03-20T13:40:00Z', originFacilityId: 'FAC-HQ01', category: WasteCategory.METALS, weightKg: 2800, destinationProvider: 'ScrapKing LLC', disposalMethod: DisposalMethod.UPCYCLED, certified: false, costUsd: 0 },
        { manifestId: 'WM-770P', timestamp: '2024-03-15T09:05:00Z', originFacilityId: 'FAC-TX09', category: WasteCategory.TEXTILES, weightKg: 450, destinationProvider: 'ThreadCycle', disposalMethod: DisposalMethod.UNKNOWN, certified: false, costUsd: 180 },
    ];
};

const generateMockFacilities = (): FacilityWasteMetrics[] => {
    return [
        { facilityId: 'FAC-HQ01', facilityName: 'Global Headquarters', region: 'NA-East', totalWasteGeneratedKg: 4890, totalDivertedKg: 4890, landfillDiversionRate: 100, hazardousRatio: 0, averageMonthlyCost: 370, auditStatus: 'Compliant' },
        { facilityId: 'FAC-MN02', facilityName: 'Primary Manufacturing Node', region: 'EMEA', totalWasteGeneratedKg: 425, totalDivertedKg: 315, landfillDiversionRate: 74.1, hazardousRatio: 25.8, averageMonthlyCost: 1650, auditStatus: 'At Risk' },
        { facilityId: 'FAC-TX09', facilityName: 'Logistics Distribution Hub', region: 'NA-South', totalWasteGeneratedKg: 5600, totalDivertedKg: 950, landfillDiversionRate: 16.9, hazardousRatio: 0, averageMonthlyCost: 1340, auditStatus: 'Non-Compliant' }
    ];
};

/**
 * Waste Data Service Global Provider
 */
export const WasteDataProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [manifests, setManifests] = useState<WasteManifestEvent[]>([]);
    const [facilities, setFacilities] = useState<FacilityWasteMetrics[]>([]);
    const [enterpriseStats, setEnterpriseStats] = useState<EnterpriseCircularMetrics | null>(null);

    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    const refreshData = useCallback(async () => {
        setIsLoading(true);
        setError(null);

        try {
            // Emulate Backend API call latency (600ms - 1.2s)
            await new Promise(resolve => setTimeout(resolve, Math.random() * 600 + 600));

            // Artificial failure condition testing 1% of time
            if (Math.random() > 0.99) throw new Error("Connection timeout: Origin Waste API.");

            const fetchedManifests = generateMockWasteManifests();
            const fetchedFacilities = generateMockFacilities();

            setManifests(fetchedManifests);
            setFacilities(fetchedFacilities);

            // Process the client-side derivations
            const stats = compileEnterpriseMetrics(fetchedManifests);
            setEnterpriseStats(stats);

        } catch (err: any) {
            console.error('[WasteDataService] Error Fetching Waste Analytics:', err);
            setError(err.message || 'REST Failure.');
        } finally {
            setIsLoading(false);
        }
    }, []);

    // Initial lifecycle hook
    useEffect(() => {
        refreshData();
    }, [refreshData]);

    return (
        <WasteContext.Provider value= {{ manifests, facilities, enterpriseStats, isLoading, error, refreshData }
}>
    { children }
    </WasteContext.Provider>
    );
};

/**
 * Guarded custom hook for extracting context values
 */
export const useWasteData = (): WasteContextState => {
    const context = useContext(WasteContext);
    if (!context) {
        throw new Error('useWasteData requires invocation within a bounded <WasteDataProvider> component.');
    }
    return context;
};
