/**
 * @file WasteCoreTypes.ts
 * @description Core TypeScript structures dictating the data architecture of the Enterprise 
 * Circular Economy Waste Management Tracker. Used to accurately classify, track, and 
 * report on corporate waste diversions (zero-waste-to-landfill tracking).
 */

/**
 * Waste categorization based on international corporate reporting standards.
 */
export enum WasteCategory {
    ORGANIC = 'Organic (Compostable)',
    PLASTIC = 'Plastics (Recyclable)',
    PAPER_CARDBOARD = 'Paper & Cardboard',
    E_WASTE = 'Electronic Waste (E-Waste)',
    HAZARDOUS = 'Hazardous Materials',
    MIXED_SOLID = 'Mixed Municipal Solid',
    TEXTILES = 'Textile Byproducts',
    METALS = 'Scrap Metals'
}

/**
 * The final destination or disposal methodology applied to the waste stream.
 */
export enum DisposalMethod {
    RECYCLED = 'Recycled (Closed Loop)',
    UPCYCLED = 'Upcycled (Value Add)',
    COMPOSTED = 'Composted',
    INCINERATED_ENERGY = 'Incinerated (Energy Recovery)',
    INCINERATED_FLARED = 'Incinerated (Flared)',
    LANDFILL = 'Landfill Deposition',
    UNKNOWN = 'Untraceable / Unknown'
}

/**
 * Data structure representing a single recorded waste generation event from a facility.
 */
export interface WasteManifestEvent {
    manifestId: string;
    timestamp: string;
    originFacilityId: string;
    category: WasteCategory;
    weightKg: number;
    destinationProvider: string;
    disposalMethod: DisposalMethod;
    certified: boolean;
    costUsd: number;
}

/**
 * Overview metrics for a specific enterprise facility outlining waste KPIs over a default time window.
 */
export interface FacilityWasteMetrics {
    facilityId: string;
    facilityName: string;
    region: string;
    totalWasteGeneratedKg: number;
    totalDivertedKg: number; // Volume that did NOT go to landfill or flare
    landfillDiversionRate: number; // Percentage 0-100
    hazardousRatio: number; // Percentage 0-100
    averageMonthlyCost: number;
    auditStatus: 'Compliant' | 'At Risk' | 'Non-Compliant';
}

/**
 * Macro enterprise-wide rollups of the circular economy health.
 */
export interface EnterpriseCircularMetrics {
    totalWasteVolumeTons: number;
    globalDiversionRate: number;
    topWasteCategory: WasteCategory;
    totalDisposalCost: number;
    scope3WasteEmissions: number; // tCO2e extrapolated from waste decomposition
    certifiedContractorsRatio: number; // Percentage
}

/* -------------------------------------------------------------------------- */
/*                                UTILITIES                                   */
/* -------------------------------------------------------------------------- */

/**
 * Validates whether a specific disposal method counts as 'Diverted' from landfill
 * according to standard Zero Waste guidelines.
 */
export const isDiverted = (method: DisposalMethod): boolean => {
    return [
        DisposalMethod.RECYCLED,
        DisposalMethod.UPCYCLED,
        DisposalMethod.COMPOSTED,
        DisposalMethod.INCINERATED_ENERGY // Sometimes counts, technically.
    ].includes(method);
};

/**
 * Extracts a Tailwind CSS color styling definition string for Waste Categories.
 * Provides visually distinct badging in the UI.
 */
export const getCategoryBadgeStyle = (category: WasteCategory): string => {
    switch (category) {
        case WasteCategory.ORGANIC:
            return 'bg-emerald-100 text-emerald-800 dark:bg-emerald-500/20 dark:text-emerald-400 border-emerald-200 dark:border-emerald-500/30';
        case WasteCategory.PLASTIC:
            return 'bg-cyan-100 text-cyan-800 dark:bg-cyan-500/20 dark:text-cyan-400 border-cyan-200 dark:border-cyan-500/30';
        case WasteCategory.PAPER_CARDBOARD:
            return 'bg-amber-100 text-amber-800 dark:bg-amber-500/20 dark:text-amber-400 border-amber-200 dark:border-amber-500/30';
        case WasteCategory.E_WASTE:
            return 'bg-purple-100 text-purple-800 dark:bg-purple-500/20 dark:text-purple-400 border-purple-200 dark:border-purple-500/30';
        case WasteCategory.HAZARDOUS:
            return 'bg-red-100 text-red-800 dark:bg-red-500/20 dark:text-red-400 border-red-200 dark:border-red-500/30';
        case WasteCategory.METALS:
            return 'bg-slate-200 text-slate-800 dark:bg-slate-600 dark:text-slate-300 border-slate-300 dark:border-slate-500';
        default:
            return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300 border-gray-200 dark:border-gray-600';
    }
};

/**
 * Calculates a derived Scope 3 emissions proxy assuming baseline decay constants.
 * Highly approximated for UI demonstration capability.
 * @param weightKg Raw mass of the waste
 * @param method How it was disposed
 * @returns Estimated metric tons of CO2 equivalent (tCO2e)
 */
export const estimateEmissionsForEvent = (weightKg: number, method: DisposalMethod): number => {
    const tons = weightKg / 1000;
    switch (method) {
        case DisposalMethod.LANDFILL: return tons * 0.52;
        case DisposalMethod.INCINERATED_FLARED: return tons * 0.95; // Direct release
        case DisposalMethod.INCINERATED_ENERGY: return tons * 0.35; // Offset by energy generated
        case DisposalMethod.COMPOSTED: return tons * 0.05; // Anaerobic vs Aerobic breakdown
        case DisposalMethod.RECYCLED: return tons * 0.02; // Processing transport costs
        case DisposalMethod.UPCYCLED: return 0; // Net zero
        default: return tons * 0.50; // Conservative aggregate average
    }
};

/**
 * Formats standard weight correctly minimizing decimal spam on UI elements.
 */
export const formatWeightKg = (kg: number): string => {
    if (kg > 1000) {
        return `${(kg / 1000).toFixed(2)} t`;
    }
    return `${kg.toFixed(0)} kg`;
};

/**
 * Summarizer function executed by the Global Data Service to derive KPIs out of 
 * a simulated database view.
 */
export const compileEnterpriseMetrics = (manifests: WasteManifestEvent[]): EnterpriseCircularMetrics => {
    let totalKg = 0;
    let divertedKg = 0;
    let totalCost = 0;
    let totalEmissions = 0;
    let certCount = 0;

    const categoryMap: Record<string, number> = {};

    manifests.forEach(evt => {
        totalKg += evt.weightKg;
        totalCost += evt.costUsd;
        totalEmissions += estimateEmissionsForEvent(evt.weightKg, evt.disposalMethod);

        if (isDiverted(evt.disposalMethod)) {
            divertedKg += evt.weightKg;
        }

        if (evt.certified) certCount++;

        if (!categoryMap[evt.category]) categoryMap[evt.category] = 0;
        categoryMap[evt.category] += evt.weightKg;
    });

    let maxWeight = 0;
    let topCat = WasteCategory.MIXED_SOLID;

    for (const [cat, w] of Object.entries(categoryMap)) {
        if (w > maxWeight) {
            maxWeight = w;
            topCat = cat as WasteCategory;
        }
    }

    return {
        totalWasteVolumeTons: totalKg / 1000,
        globalDiversionRate: totalKg > 0 ? (divertedKg / totalKg) * 100 : 0,
        topWasteCategory: topCat,
        totalDisposalCost: totalCost,
        scope3WasteEmissions: totalEmissions,
        certifiedContractorsRatio: manifests.length > 0 ? (certCount / manifests.length) * 100 : 0
    };
};
