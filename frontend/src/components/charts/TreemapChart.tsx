"use client";

import dynamic from 'next/dynamic';
import { motion } from 'framer-motion';

const ResponsiveContainer = dynamic(() => import('recharts').then(mod => mod.ResponsiveContainer), { ssr: false });
const Treemap = dynamic(() => import('recharts').then(mod => mod.Treemap), { ssr: false });
const Tooltip = dynamic(() => import('recharts').then(mod => mod.Tooltip), { ssr: false });



interface TreemapChartProps {
    data: Record<string, any>[];
    dataKey?: string;
    onDrillDown?: (platform: string) => void;
}

const COLORS = [
    '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
    '#06b6d4', '#ec4899', '#84cc16', '#f97316', '#6366f1'
];

interface CustomContentProps {
    x: number;
    y: number;
    width: number;
    height: number;
    index: number;
    name: string;
    value: number;
    onDrillDown?: (name: string) => void;
}

const CustomContent = (props: any) => {
    const { x, y, width, height, index, name, value, onDrillDown } = props;
    if (width < 50 || height < 30) return null;

    return (
        <g>
            <motion.rect
                x={x}
                y={y}
                width={width}
                height={height}
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ delay: index * 0.05 }}
                style={{
                    fill: COLORS[index % COLORS.length],
                    stroke: '#fff',
                    strokeWidth: 2,
                    cursor: 'pointer'
                }}
                rx={4}
                onClick={() => onDrillDown?.(name)}
            />
            <text
                x={x + width / 2}
                y={y + height / 2 - 8}
                textAnchor="middle"
                fill="#fff"
                fontSize={12}
                fontWeight="bold"
            >
                {name}
            </text>
            <text
                x={x + width / 2}
                y={y + height / 2 + 10}
                textAnchor="middle"
                fill="#fff"
                fontSize={11}
                opacity={0.9}
            >
                ${typeof value === 'number' ? value.toLocaleString() : value}
            </text>
        </g>
    );
};

export function TreemapChart({ data, dataKey = 'spend', onDrillDown }: TreemapChartProps) {
    // Transform data for treemap format
    const treemapData = data.map((item, index) => ({
        name: item.name || item.platform,
        size: item[dataKey] || item.value || 0,
        fill: COLORS[index % COLORS.length]
    }));

    return (
        <ResponsiveContainer width="100%" height="100%">
            <Treemap
                data={treemapData}
                dataKey="size"
                aspectRatio={4 / 3}
                stroke="#fff"
                fill="#3b82f6"
                content={<CustomContent onDrillDown={onDrillDown} /> as any}
            >
                <Tooltip
                    formatter={((value: any) => [`$${Number(value).toLocaleString()}`, 'Spend']) as any}
                    contentStyle={{
                        backgroundColor: 'hsl(var(--card))',
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '8px'
                    }}
                />
            </Treemap>
        </ResponsiveContainer>
    );
}
