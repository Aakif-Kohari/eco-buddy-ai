import React from 'react';
import { useSupplierRisk } from './SupplierRiskService';
import { SupplierTier, getHexAliasForTailwind } from './SupplyChainCoreTypes';

/**
 * Renders a CSS-based Node Graph layout utilizing nested Flexbox trees
 * to avoid heavy d3.js or external canvas dependencies while retaining high-velocity structure.
 */
const SupplierNodeGraph: React.FC = () => {
    const { nodes } = useSupplierRisk();

    const t1 = nodes.filter(n => n.tier === SupplierTier.TIER_1);
    const t2 = nodes.filter(n => n.tier === SupplierTier.TIER_2);
    const t3 = nodes.filter(n => n.tier === SupplierTier.TIER_3);

    const renderColumn = (columnNodes: typeof nodes, title: string) => (
        <div className="flex flex-col h-full items-center justify-center gap-6 z-10 w-1/3 p-4">
            <h4 className="text-xs font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500 mb-2">{title}</h4>
            <div className="w-full flex w-full flex-col gap-6">
                {columnNodes.map(node => {
                    const badgeStyle = getHexAliasForTailwind(node.risk);
                    return (
                        <div
                            key={node.id}
                            className={`relative px-4 py-3 rounded-xl border-2 bg-white dark:bg-slate-800 backdrop-blur-md shadow-sm transition-all hover:-translate-y-1 hover:shadow-lg cursor-pointer ${badgeStyle}`}
                            title={`Emissions: ${node.metrics.scope3Emissions} tCO2e | Score: ${node.metrics.auditScore}`}
                        >
                            <div className="text-xs text-slate-500 dark:text-slate-400 font-mono mb-0.5">{node.id}</div>
                            <div className="font-bold text-sm text-slate-800 dark:text-white leading-tight truncate">{node.name}</div>
                            <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-200 dark:border-slate-700/50">
                                <span className="text-[10px] font-semibold flex items-center">
                                    <span className={`w-1.5 h-1.5 rounded-full mr-1.5 ${badgeStyle.split(' ')[0].replace('text-', 'bg-')}`}></span>
                                    {node.risk.replace('Risk', '').trim()}
                                </span>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );

    return (
        <div className="w-full h-full min-h-[400px] flex relative overflow-x-auto p-4 custom-scrollbar">
            {/* SVG Connecting Lines Background Layer Mock */}
            <div className="absolute inset-0 z-0 pointer-events-none opacity-20 dark:opacity-30">
                <svg width="100%" height="100%" style={{ strokeDasharray: '4,4' }}>
                    <path d="M 150 200 Q 300 100 450 250" stroke="#94a3b8" strokeWidth="2" fill="none" />
                    <path d="M 150 200 Q 300 400 450 250" stroke="#94a3b8" strokeWidth="2" fill="none" />
                    <path d="M 450 250 Q 600 500 750 400" stroke="#94a3b8" strokeWidth="2" fill="none" />
                </svg>
            </div>

            {renderColumn(t3, 'Tier 3 / Origins')}
            {renderColumn(t2, 'Tier 2')}
            {renderColumn(t1, 'Tier 1 / Direct')}
        </div>
    );
};

export default SupplierNodeGraph;
