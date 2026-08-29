import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { SupplyChainNode, RiskLevel, SupplierTier, AnalyticsSummary, calculateSummary } from './SupplyChainCoreTypes';

interface SupplierContextState {
    nodes: SupplyChainNode[];
    summary: AnalyticsSummary | null;
    isLoading: boolean;
    error: string | null;
    refreshData: () => Promise<void>;
}

const generateMockNodes = (): SupplyChainNode[] => {
    return [
        {
            id: 'SUP-001', name: 'Global Logistics Corp', tier: SupplierTier.TIER_1, country: 'USA',
            coordinates: { lat: 34.0522, lng: -118.2437 }, risk: RiskLevel.MODERATE,
            metrics: { annualSpendUsd: 12500000, scope3Emissions: 45000, dataCompleteness: 92, auditScore: 88 },
            primaryCategory: 'Transportation', parentIds: [], lastAssessed: '2024-03-01T10:00:00Z'
        },
        {
            id: 'SUP-002', name: 'Alba Manufacturing Ltd.', tier: SupplierTier.TIER_1, country: 'Mexico',
            coordinates: { lat: 25.6866, lng: -100.3161 }, risk: RiskLevel.HIGH,
            metrics: { annualSpendUsd: 28000000, scope3Emissions: 120500, dataCompleteness: 65, auditScore: 54 },
            primaryCategory: 'Component Assembly', parentIds: [], lastAssessed: '2024-02-15T09:30:00Z'
        },
        {
            id: 'SUP-003', name: 'SinoTech Materials', tier: SupplierTier.TIER_2, country: 'China',
            coordinates: { lat: 22.5431, lng: 114.0579 }, risk: RiskLevel.CRITICAL,
            metrics: { annualSpendUsd: 8500000, scope3Emissions: 220000, dataCompleteness: 40, auditScore: 35 },
            primaryCategory: 'Rare Earth Metals', parentIds: ['SUP-002'], lastAssessed: '2023-11-20T14:15:00Z'
        },
        {
            id: 'SUP-004', name: 'Nordic Packaging Inc.', tier: SupplierTier.TIER_1, country: 'Sweden',
            coordinates: { lat: 59.3293, lng: 18.0686 }, risk: RiskLevel.LOW,
            metrics: { annualSpendUsd: 4200000, scope3Emissions: 2100, dataCompleteness: 98, auditScore: 96 },
            primaryCategory: 'Sustainable Packaging', parentIds: [], lastAssessed: '2024-04-10T11:00:00Z'
        },
        {
            id: 'SUP-005', name: 'Atacama Lithium Co.', tier: SupplierTier.TIER_3, country: 'Chile',
            coordinates: { lat: -23.8634, lng: -69.1328 }, risk: RiskLevel.HIGH,
            metrics: { annualSpendUsd: 1400000, scope3Emissions: 40500, dataCompleteness: 75, auditScore: 62 },
            primaryCategory: 'Raw Minerals', parentIds: ['SUP-003', 'SUP-007'], lastAssessed: '2023-12-05T08:45:00Z'
        },
        {
            id: 'SUP-006', name: 'GreenEnergy Providers LLC', tier: SupplierTier.TIER_2, country: 'Germany',
            coordinates: { lat: 51.1657, lng: 10.4515 }, risk: RiskLevel.LOW,
            metrics: { annualSpendUsd: 6500000, scope3Emissions: 450, dataCompleteness: 100, auditScore: 99 },
            primaryCategory: 'Renewable Power', parentIds: ['SUP-001', 'SUP-004'], lastAssessed: '2024-04-20T13:20:00Z'
        },
        {
            id: 'SUP-007', name: 'Oceanic Shipping Conglomerate', tier: SupplierTier.TIER_2, country: 'Singapore',
            coordinates: { lat: 1.3521, lng: 103.8198 }, risk: RiskLevel.MODERATE,
            metrics: { annualSpendUsd: 18000000, scope3Emissions: 210000, dataCompleteness: 85, auditScore: 78 },
            primaryCategory: 'Maritime Freight', parentIds: ['SUP-001'], lastAssessed: '2024-01-18T16:00:00Z'
        }
    ];
};

const SupplierRiskContext = createContext<SupplierContextState | undefined>(undefined);

export const SupplierRiskProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [nodes, setNodes] = useState<SupplyChainNode[]>([]);
    const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    const refreshData = async () => {
        setIsLoading(true);
        setError(null);

        try {
            // Simulating API Latency
            await new Promise(resolve => setTimeout(resolve, 600));

            const fetchedNodes = generateMockNodes();
            setNodes(fetchedNodes);
            setSummary(calculateSummary(fetchedNodes));

        } catch (err: any) {
            setError(err.message || 'Failed to sync supply chain graphs.');
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        refreshData();
    }, []);

    return (
        <SupplierRiskContext.Provider value= {{ nodes, summary, isLoading, error, refreshData }
}>
    { children }
    </SupplierRiskContext.Provider>
    );
};

export const useSupplierRisk = (): SupplierContextState => {
    const context = useContext(SupplierRiskContext);
    if (!context) {
        throw new Error('useSupplierRisk must be used within a SupplierRiskProvider');
    }
    return context;
};
