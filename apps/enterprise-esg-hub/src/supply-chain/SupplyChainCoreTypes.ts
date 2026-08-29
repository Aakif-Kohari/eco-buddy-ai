// Core TypeScript Interfaces and Enums for Supply Chain Module

export enum SupplierTier {
    TIER_1 = 'Tier 1 (Direct)',
    TIER_2 = 'Tier 2 (Indirect)',
    TIER_3 = 'Tier 3 (Raw Materials)',
}

export enum RiskLevel {
    LOW = 'Low Risk',
    MODERATE = 'Moderate Risk',
    HIGH = 'High Risk',
    CRITICAL = 'Critical Risk',
}

export interface Coordinates {
    lat: number;
    lng: number;
}

export interface SupplierMetrics {
    annualSpendUsd: number;
    scope3Emissions: number; // in tCO2e
    dataCompleteness: number; // percentage
    auditScore: number; // 0-100
}

export interface SupplyChainNode {
    id: string;
    name: string;
    tier: SupplierTier;
    country: string;
    coordinates: Coordinates;
    risk: RiskLevel;
    metrics: SupplierMetrics;
    primaryCategory: string;
    parentIds: string[]; // Links to calculate flow
    lastAssessed: string; // ISO Date String
}

export interface AnalyticsSummary {
    totalSuppliers: number;
    totalScope3Emissions: number;
    highRiskCount: number;
    tierDistribution: Record<SupplierTier, number>;
    averageDataQuality: number;
}

// Utility functions for sorting and typing

export const parseRiskToValue = (risk: RiskLevel): number => {
    switch (risk) {
        case RiskLevel.CRITICAL: return 4;
        case RiskLevel.HIGH: return 3;
        case RiskLevel.MODERATE: return 2;
        case RiskLevel.LOW: return 1;
        default: return 0;
    }
};

export const getColorForRisk = (risk: RiskLevel): string => {
    switch (risk) {
        case RiskLevel.CRITICAL: return '#ef4444'; // Red 500
        case RiskLevel.HIGH: return '#f97316'; // Orange 500
        case RiskLevel.MODERATE: return '#eab308'; // Yellow 500
        case RiskLevel.LOW: return '#10b981'; // Emerald 500
        default: return '#94a3b8'; // Slate 400
    }
};

export const getHexAliasForTailwind = (risk: RiskLevel): string => {
    switch (risk) {
        case RiskLevel.CRITICAL: return 'text-red-500 bg-red-500/10 border-red-500/20';
        case RiskLevel.HIGH: return 'text-orange-500 bg-orange-500/10 border-orange-500/20';
        case RiskLevel.MODERATE: return 'text-yellow-600 bg-yellow-500/10 border-yellow-500/20';
        case RiskLevel.LOW: return 'text-emerald-500 bg-emerald-500/10 border-emerald-500/20';
        default: return 'text-slate-500 bg-slate-500/10 border-slate-500/20';
    }
};

export const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
    }).format(amount);
};

export const calculateSummary = (nodes: SupplyChainNode[]): AnalyticsSummary => {
    const totalScope3 = nodes.reduce((sum, n) => sum + n.metrics.scope3Emissions, 0);
    const highRisk = nodes.filter(n => n.risk === RiskLevel.HIGH || n.risk === RiskLevel.CRITICAL).length;
    const avgDataQuality = nodes.reduce((sum, n) => sum + n.metrics.dataCompleteness, 0) / (nodes.length || 1);

    const distro = {
        [SupplierTier.TIER_1]: nodes.filter(n => n.tier === SupplierTier.TIER_1).length,
        [SupplierTier.TIER_2]: nodes.filter(n => n.tier === SupplierTier.TIER_2).length,
        [SupplierTier.TIER_3]: nodes.filter(n => n.tier === SupplierTier.TIER_3).length,
    };

    return {
        totalSuppliers: nodes.length,
        totalScope3Emissions: totalScope3,
        highRiskCount: highRisk,
        tierDistribution: distro,
        averageDataQuality: avgDataQuality,
    };
};
