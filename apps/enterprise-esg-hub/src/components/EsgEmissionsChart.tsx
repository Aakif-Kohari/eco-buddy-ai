import React from 'react';
import {
    ResponsiveContainer,
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ReferenceLine
} from 'recharts';

export interface EmissionsDataPoint {
    year: string;
    scope1: number;
    scope2: number;
    scope3: number;
    target: number;
}

interface EsgEmissionsChartProps {
    data: EmissionsDataPoint[];
}

export const EsgEmissionsChart: React.FC<EsgEmissionsChartProps> = ({ data }) => {

    // Custom tooltip for premium look
    const CustomTooltip = ({ active, payload, label }: any) => {
        if (active && payload && payload.length) {
            return (
                <div className="bg-slate-900/90 backdrop-blur-md border border-slate-700 p-4 rounded-xl shadow-2xl text-white min-w-[200px]">
                    <p className="font-bold text-lg mb-3 pb-2 border-b border-slate-700">{label}</p>
                    {payload.map((entry: any, index: number) => (
                        <div key={index} className="flex justify-between items-center py-1">
                            <div className="flex items-center gap-2">
                                <span
                                    className="w-3 h-3 rounded-full"
                                    style={{ backgroundColor: entry.color }}
                                ></span>
                                <span className="text-sm font-medium text-slate-300">
                                    {entry.name}
                                </span>
                            </div>
                            <span className="font-bold text-sm font-mono ml-4">
                                {entry.value.toLocaleString()} <span className="text-xs text-slate-500">tCO2e</span>
                            </span>
                        </div>
                    ))}
                    <div className="mt-3 pt-3 border-t border-slate-700 flex justify-between items-center">
                        <span className="text-sm font-medium text-slate-400">Total</span>
                        <span className="font-bold text-emerald-400 font-mono">
                            {payload.reduce((sum: number, entry: any) => sum + entry.value, 0).toLocaleString()}
                        </span>
                    </div>
                </div>
            );
        }
        return null;
    };

    if (!data || data.length === 0) {
        return (
            <div className="w-full h-full flex items-center justify-center bg-slate-50 dark:bg-slate-900/50 rounded-xl border border-dashed border-slate-300 dark:border-slate-700">
                <span className="text-slate-500">No trajectory data available.</span>
            </div>
        );
    }

    return (
        <div className="w-full h-[400px]">
            <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                    data={data}
                    margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                >
                    <defs>
                        <linearGradient id="colorScope1" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                        </linearGradient>
                        <linearGradient id="colorScope2" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0} />
                        </linearGradient>
                        <linearGradient id="colorScope3" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.0} />
                        </linearGradient>
                    </defs>

                    <CartesianGrid
                        strokeDasharray="3 3"
                        vertical={false}
                        stroke="#334155"
                        opacity={0.3}
                    />

                    <XAxis
                        dataKey="year"
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: '#64748b', fontSize: 13, fontWeight: 500 }}
                        dy={10}
                    />

                    <YAxis
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: '#64748b', fontSize: 12 }}
                        tickFormatter={(val) => `${(val / 1000)}k`}
                        dx={-10}
                    />

                    <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#475569', strokeWidth: 1, strokeDasharray: '4 4' }} />

                    <Legend
                        verticalAlign="top"
                        height={36}
                        iconType="circle"
                        wrapperStyle={{ paddingBottom: '20px', fontSize: '14px', fontWeight: 500, color: '#94a3b8' }}
                    />

                    {/* Scientific target line */}
                    <ReferenceLine
                        y={400000}
                        label={{ position: 'top', value: '2030 Interim Target', fill: '#ef4444', fontSize: 12, fontWeight: 700 }}
                        stroke="#ef4444"
                        strokeDasharray="5 5"
                        strokeWidth={2}
                        opacity={0.8}
                    />

                    <Area
                        type="monotone"
                        dataKey="scope3"
                        name="Scope 3 (Value Chain)"
                        stroke="#f59e0b"
                        strokeWidth={3}
                        fillOpacity={1}
                        fill="url(#colorScope3)"
                        animationDuration={2000}
                    />
                    <Area
                        type="monotone"
                        dataKey="scope2"
                        name="Scope 2 (Indirect Energy)"
                        stroke="#3b82f6"
                        strokeWidth={3}
                        fillOpacity={1}
                        fill="url(#colorScope2)"
                        animationDuration={1500}
                    />
                    <Area
                        type="monotone"
                        dataKey="scope1"
                        name="Scope 1 (Direct Source)"
                        stroke="#10b981"
                        strokeWidth={3}
                        fillOpacity={1}
                        fill="url(#colorScope1)"
                        animationDuration={1000}
                    />
                </AreaChart>
            </ResponsiveContainer>
        </div>
    );
};

export default EsgEmissionsChart;
