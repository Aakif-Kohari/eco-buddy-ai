import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

/**
 * CORE DATA TYPES FOR ESG HUB
 */
export interface EsgKPIs {
    scope1: number;
    scope2: number;
    scope3: number;
    intensity: number;
}

export interface EmissionsDataPoint {
    year: string;
    scope1: number;
    scope2: number;
    scope3: number;
    target: number;
}

export interface OffsetTransaction {
    id: string;
    date: string;
    project: string;
    type: 'Forestry' | 'Renewable Energy' | 'Methane Capture' | 'Direct Air Capture';
    amount: number;
    status: 'Verified' | 'Pending' | 'Failed';
    provider: string;
}

interface EsgContextState {
    kpiData: EsgKPIs | null;
    timelineData: EmissionsDataPoint[];
    transactions: OffsetTransaction[];
    isLoading: boolean;
    error: string | null;
    fetchMetrics: () => Promise<void>;
}

// Default state instantiation
const EsgContext = createContext<EsgContextState | undefined>(undefined);

// MOCK DATA GENERATORS (Representing Production Data fetching from Backend API)
const generateMockKpis = (): EsgKPIs => ({
    scope1: 424500,
    scope2: 112300,
    scope3: 1894200,
    intensity: 14.2
});

const generateMockTimeline = (): EmissionsDataPoint[] => ([
    { year: '2019', scope1: 520000, scope2: 150000, scope3: 2000000, target: 1800000 },
    { year: '2020', scope1: 450000, scope2: 145000, scope3: 1500000, target: 1750000 },
    { year: '2021', scope1: 460000, scope2: 140000, scope3: 1650000, target: 1700000 },
    { year: '2022', scope1: 440000, scope2: 130000, scope3: 1750000, target: 1650000 },
    { year: '2023', scope1: 430000, scope2: 120000, scope3: 1800000, target: 1600000 },
    { year: '2024', scope1: 424500, scope2: 112300, scope3: 1894200, target: 1550000 },
]);

const generateMockTransactions = (): OffsetTransaction[] => ([
    { id: 'TX-8924A', date: '2024-03-12', project: 'Amazon Bio-Reserve Alpha', type: 'Forestry', amount: 15000, status: 'Verified', provider: 'EcoAssets Mgmt' },
    { id: 'TX-8912B', date: '2024-02-28', project: 'Sahara Solar Initiative V', type: 'Renewable Energy', amount: 8400, status: 'Verified', provider: 'Verra Standard' },
    { id: 'TX-8805F', date: '2024-02-15', project: 'North Sea Wind Project', type: 'Renewable Energy', amount: 12000, status: 'Pending', provider: 'Gold Standard' },
    { id: 'TX-8799C', date: '2024-01-30', project: 'Agri-Methane Capture UK', type: 'Methane Capture', amount: 5200, status: 'Verified', provider: 'Climate Action Reserve' },
    { id: 'TX-8650D', date: '2023-11-22', project: 'Climeworks DAC Beta', type: 'Direct Air Capture', amount: 1200, status: 'Verified', provider: 'Puro.earth' },
    { id: 'TX-8642A', date: '2023-11-05', project: 'Indonesia Mangrove Restoration', type: 'Forestry', amount: 22000, status: 'Failed', provider: 'EcoAssets Mgmt' },
    { id: 'TX-8501X', date: '2023-10-18', project: 'Texas Solar Grid Expansion', type: 'Renewable Energy', amount: 16500, status: 'Verified', provider: 'Verra Standard' },
]);

/**
 * Service API Abstraction (Simulating HTTP Fetch)
 */
class ESGDataService {
    static async fetchDashboardData(): Promise<{ kpis: EsgKPIs, timeline: EmissionsDataPoint[], transactions: OffsetTransaction[] }> {
        // Simulate network latency (800ms to 1.5s)
        const delay = Math.random() * 800 + 800;

        return new Promise((resolve, reject) => {
            setTimeout(() => {
                // Simulate occasional network error (5% chance)
                if (Math.random() > 0.95) {
                    reject(new Error("Network Error: Unable to reach Enterprise ESG Aggregator Service."));
                } else {
                    resolve({
                        kpis: generateMockKpis(),
                        timeline: generateMockTimeline(),
                        transactions: generateMockTransactions()
                    });
                }
            }, delay);
        });
    }
}

/**
 * Provider Component for Global State Injection
 */
export const EsgMetricsProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [kpiData, setKpiData] = useState<EsgKPIs | null>(null);
    const [timelineData, setTimelineData] = useState<EmissionsDataPoint[]>([]);
    const [transactions, setTransactions] = useState<OffsetTransaction[]>([]);

    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    const fetchMetrics = async () => {
        setIsLoading(true);
        setError(null);
        try {
            const data = await ESGDataService.fetchDashboardData();
            setKpiData(data.kpis);
            setTimelineData(data.timeline);
            setTransactions(data.transactions);
        } catch (err: any) {
            console.error("Failed to sync ESG metrics:", err);
            setError(err.message || "An unknown error occurred while syncing ESG data.");
        } finally {
            setIsLoading(false);
        }
    };

    // Auto-fetch on mount
    useEffect(() => {
        fetchMetrics();
    }, []);

    // Polling mechanism for live production data (simulated 5 minute polling)
    useEffect(() => {
        const interval = setInterval(() => {
            console.log("[ESG Service] Background sync triggered.");
            // Silent refresh in background
            ESGDataService.fetchDashboardData()
                .then(data => {
                    setKpiData(data.kpis);
                    setTimelineData(data.timeline);
                    setTransactions(data.transactions);
                })
                .catch(e => console.warn("Background sync failed:", e));
        }, 300000);
        return () => clearInterval(interval);
    }, []);

    return (
        <EsgContext.Provider value= {{ kpiData, timelineData, transactions, isLoading, error, fetchMetrics }
}>
    { children }
    </EsgContext.Provider>
    );
};

/**
 * Custom Hook for accessing ESG Metrics
 */
export const useEsgMetrics = (): EsgContextState => {
    const context = useContext(EsgContext);
    if (context === undefined) {
        throw new Error('useEsgMetrics must be used within an EsgMetricsProvider');
    }
    return context;
};
