import React, { useState } from 'react';

export interface MaterialComponent {
  materialName: string;
  weightKg: number;
  recycledContentPct: number;
  recyclabilityRatePct: number;
  embodiedCarbonKgCo2: number;
}

export interface CircularProductItem {
  productId: string;
  productName: string;
  category: string;
  totalWeightKg: number;
  mciScore: number;
  landfillDiversionPct: number;
  embodiedCarbonTotal: number;
  components: MaterialComponent[];
  eolPathway: string;
  createdAt: string;
}

export const CircularEconomyStudioView: React.FC = () => {
  const [products] = useState<CircularProductItem[]>([
    {
      productId: 'CIRC-101',
      productName: 'EcoModule Industrial Enclosure',
      category: 'Industrial Hardware',
      totalWeightKg: 6.9,
      mciScore: 0.91,
      landfillDiversionPct: 94.5,
      embodiedCarbonTotal: 16.7,
      eolPathway: 'Closed-Loop Takeback & Remanufacturing',
      createdAt: '2026-08-22 06:20:00',
      components: [
        {
          materialName: 'Post-Consumer Recycled Aluminum (PCR-AL)',
          weightKg: 4.2,
          recycledContentPct: 85.0,
          recyclabilityRatePct: 98.0,
          embodiedCarbonKgCo2: 12.4,
        },
        {
          materialName: 'Bio-Based Polypropylene',
          weightKg: 2.7,
          recycledContentPct: 90.0,
          recyclabilityRatePct: 88.0,
          embodiedCarbonKgCo2: 4.3,
        },
      ],
    },
    {
      productId: 'CIRC-102',
      productName: 'EcoFiber Packaging Matrix',
      category: 'Packaging Solutions',
      totalWeightKg: 1.5,
      mciScore: 0.96,
      landfillDiversionPct: 98.0,
      embodiedCarbonTotal: 2.1,
      eolPathway: 'Industrial Composting',
      createdAt: '2026-08-22 06:22:00',
      components: [
        {
          materialName: 'Unbleached Bamboo Fiber',
          weightKg: 1.5,
          recycledContentPct: 100.0,
          recyclabilityRatePct: 100.0,
          embodiedCarbonKgCo2: 2.1,
        },
      ],
    },
  ]);

  const [selectedProduct, setSelectedProduct] = useState<CircularProductItem | null>(null);
  const [search, setSearch] = useState('');

  const filteredProducts = products.filter(
    (p) =>
      p.productName.toLowerCase().includes(search.toLowerCase()) ||
      p.productId.toLowerCase().includes(search.toLowerCase()) ||
      p.category.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-10 font-sans space-y-8">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 border-b border-slate-800 pb-6">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider">
              Circular Economy Studio
            </span>
            <span className="bg-blue-500/10 text-blue-400 border border-blue-500/20 text-xs font-bold px-3 py-1 rounded-full font-mono">
              Ellen MacArthur MCI Verified
            </span>
          </div>
          <h1 className="text-3xl md:text-4xl font-black text-white tracking-tight">
            Enterprise Circular Economy Lifecycle Studio
          </h1>
          <p className="text-sm text-slate-400 mt-1 max-w-3xl">
            Product Lifecycle Assessment (LCA), Material Circularity Index (MCI) scoring, and Scope 3 landfill diversion telemetry.
          </p>
        </div>
      </div>

      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search circular products by ID, name, or category..."
          className="w-full bg-slate-950 border border-slate-800 focus:border-emerald-500 rounded-xl px-4 py-2.5 text-xs text-slate-200 outline-none"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {filteredProducts.map((p) => (
          <div
            key={p.productId}
            className="bg-slate-900/80 backdrop-blur-md border border-slate-800 hover:border-emerald-500/50 rounded-2xl p-6 shadow-xl flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-mono font-bold text-slate-400 bg-slate-950 px-2.5 py-1 rounded border border-slate-800">
                  {p.productId}
                </span>
                <span className="text-xs font-bold px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                  MCI: {p.mciScore}
                </span>
              </div>
              <h3 className="text-xl font-black text-white mb-1">{p.productName}</h3>
              <p className="text-xs text-slate-400 mb-4">{p.category} • EOL: {p.eolPathway}</p>

              <div className="grid grid-cols-2 gap-3 bg-slate-950/60 p-3.5 rounded-xl border border-slate-800 mb-5">
                <div>
                  <span className="text-[11px] text-slate-400 block">Landfill Diversion</span>
                  <span className="text-lg font-black text-emerald-400">{p.landfillDiversionPct}%</span>
                </div>
                <div>
                  <span className="text-[11px] text-slate-400 block">Embodied Carbon</span>
                  <span className="text-lg font-black text-blue-400">{p.embodiedCarbonTotal} kg CO2e</span>
                </div>
              </div>
            </div>

            <button
              onClick={() => setSelectedProduct(p)}
              className="w-full py-2.5 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs transition-all shadow-lg"
            >
              Inspect Material Breakdown
            </button>
          </div>
        ))}
      </div>

      {selectedProduct && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-xl w-full space-y-4">
            <h2 className="text-xl font-bold text-white">{selectedProduct.productName} Breakdown</h2>
            {selectedProduct.components.map((c, idx) => (
              <div key={idx} className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 text-xs space-y-1">
                <div className="flex justify-between font-bold text-emerald-400">
                  <span>{c.materialName}</span>
                  <span>{c.weightKg} kg</span>
                </div>
                <p className="text-slate-400">Recycled Content: {c.recycledContentPct}% | Recyclability Rate: {c.recyclabilityRatePct}%</p>
              </div>
            ))}
            <button
              onClick={() => setSelectedProduct(null)}
              className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-xl"
            >
              Close Breakdown
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
