import React, { useState } from 'react';

interface WasteTip {
  id: string;
  category: 'Recycling' | 'Segregation' | 'Reuse' | 'Reduction';
  title: string;
  description: string;
  actionableStep: string;
}

const WASTE_TIPS: WasteTip[] = [
  {
    id: '1',
    category: 'Segregation',
    title: 'Dry vs. Wet Waste Separation',
    description: 'Separating organic kitchen waste from dry recyclables prevents contamination and enables proper composting.',
    actionableStep: 'Keep two separate bins in your kitchen: one for food scraps and one for plastics/paper.',
  },
  {
    id: '2',
    category: 'Reuse',
    title: 'Upcycling Glass and Containers',
    description: 'Glass jars and plastic containers can easily be cleaned and repurposed for storage or planters.',
    actionableStep: 'Wash and save 3 glass jars this week to organize pantry items.',
  },
  {
    id: '3',
    category: 'Reduction',
    title: 'Eliminating Single-Use Plastics',
    description: 'Single-use carry bags and plastic straws account for a massive share of unmanageable landfill waste.',
    actionableStep: 'Keep a reusable cloth bag and steel water bottle in your daily backpack.',
  },
  {
    id: '4',
    category: 'Recycling',
    title: 'Proper E-Waste Disposal',
    description: 'Old cables, batteries, and electronics contain toxic materials that should never go into household bins.',
    actionableStep: 'Gather old broken chargers and drop them off at a certified local e-waste collection drive.',
  },
];

export const WasteHabitsView: React.FC = () => {
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [completedTips, setCompletedTips] = useState<Record<string, boolean>>({});

  const categories = ['All', 'Segregation', 'Reuse', 'Reduction', 'Recycling'];

  const filteredTips = selectedCategory === 'All' 
    ? WASTE_TIPS 
    : WASTE_TIPS.filter(t => t.category === selectedCategory);

  const toggleTipCompletion = (id: string) => {
    setCompletedTips(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const completedCount = Object.values(completedTips.filter(Boolean)).length; // Quick count

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 text-slate-800 dark:text-slate-100">
      {/* Header */}
      <div className="mb-8 border-b pb-4 border-slate-200 dark:border-slate-700">
        <span className="text-sm font-semibold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">
          Eco-Buddy &bull; Sustainable Lifestyle
        </span>
        <h1 className="text-3xl font-bold mt-1">Everyday Waste Habits</h1>
        <p className="text-slate-600 dark:text-slate-300 mt-2">
          Build better habits around waste generation, conscious disposal, recycling, and reduction to minimize your environmental footprint.
        </p>
      </div>

      {/* Filter Tabs */}
      <div className="flex flex-wrap gap-2 mb-6">
        {categories.map(cat => (
          <button
            key={cat}
            onClick={() => setSelectedCategory(cat)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              selectedCategory === cat
                ? 'bg-emerald-600 text-white shadow-sm'
                : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Tips Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {filteredTips.map(tip => {
          const isDone = completedTips[tip.id];
          return (
            <div 
              key={tip.id}
              className={`p-6 rounded-xl border transition-all ${
                isDone 
                  ? 'bg-emerald-50/50 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-900 opacity-80' 
                  : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 shadow-sm'
              }`}
            >
              <div className="flex justify-between items-start mb-3">
                <span className="text-xs font-bold uppercase tracking-wider px-2.5 py-1 rounded-full bg-emerald-100 dark:bg-emerald-900/50 text-emerald-800 dark:text-emerald-300">
                  {tip.category}
                </span>
                <button
                  onClick={() => toggleTipCompletion(tip.id)}
                  className={`text-xs font-semibold px-3 py-1 rounded-lg border transition-colors ${
                    isDone 
                      ? 'bg-emerald-600 text-white border-emerald-600' 
                      : 'border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 hover:border-emerald-500'
                  }`}
                >
                  {isDone ? 'Completed ✓' : 'Mark as Done'}
                </button>
              </div>

              <h3 className="text-xl font-semibold mb-2">{tip.title}</h3>
              <p className="text-sm text-slate-600 dark:text-slate-300 mb-4">{tip.description}</p>
              
              <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-700/50 text-xs text-slate-700 dark:text-slate-300">
                <strong>Actionable Step:</strong> {tip.actionableStep}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
