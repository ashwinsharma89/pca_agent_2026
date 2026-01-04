"use client";

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { ResponsiveContainer, ComposedChart, CartesianGrid, XAxis, YAxis, Tooltip, Legend, Bar, Line } from 'recharts';
import { ArrowUpRight } from 'lucide-react';

interface ComparisonChartProps {
    title: string;
    description: string;
    data: any[];
    xKey: string;
    yLeftKey: string;
    yRightKey: string;
    yLeftName: string;
    yRightName: string;
    yLeftColor?: string;
    yRightColor?: string;
    height?: number;
    yLeftFormatter?: (value: number) => string;
    yRightFormatter?: (value: number) => string;
    limit?: number;
}

export function ComparisonChart({
    title,
    description,
    data,
    xKey,
    yLeftKey,
    yRightKey,
    yLeftName,
    yRightName,
    yLeftColor = "#06b6d4", // Cyan default
    yRightColor = "#10b981", // Emerald default
    height = 350,
    yLeftFormatter,
    yRightFormatter,
    limit = 10
}: ComparisonChartProps) {
    const defaultFormatter = (value: number) => {
        if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
        if (value >= 1000) return `${(value / 1000).toFixed(1)}k`;
        return value.toString();
    };

    const leftFormatter = yLeftFormatter || defaultFormatter;
    const rightFormatter = yRightFormatter || defaultFormatter;

    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                    <ArrowUpRight className="h-4 w-4 text-muted-foreground" />
                    {title}
                </CardTitle>
                <CardDescription className="text-xs">{description}</CardDescription>
            </CardHeader>
            <CardContent style={{ height: `${height}px` }}>
                {data && data.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart data={data.slice(0, limit)}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
                            <XAxis
                                dataKey={xKey}
                                tick={{ fill: '#9ca3af', fontSize: 11 }}
                                angle={-30}
                                textAnchor="end"
                                height={60}
                                interval={0}
                            />
                            <YAxis
                                yAxisId="left"
                                tick={{ fill: '#9ca3af', fontSize: 10 }}
                                tickFormatter={leftFormatter}
                                label={{ value: yLeftName, angle: -90, position: 'insideLeft', fill: '#9ca3af', fontSize: 10, dy: 40 }}
                            />
                            <YAxis
                                yAxisId="right"
                                orientation="right"
                                tick={{ fill: '#9ca3af', fontSize: 10 }}
                                tickFormatter={rightFormatter}
                                label={{ value: yRightName, angle: 90, position: 'insideRight', fill: '#9ca3af', fontSize: 10, dy: 40 }}
                            />
                            <Tooltip
                                contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px', fontSize: '12px' }}
                                labelStyle={{ color: '#f9fafb', fontWeight: 'bold', marginBottom: '4px' }}
                                formatter={(value: number, name: string) => [
                                    name === yLeftName ? leftFormatter(value) : rightFormatter(value),
                                    name
                                ]}
                            />
                            <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                            <Bar
                                yAxisId="left"
                                dataKey={yLeftKey}
                                name={yLeftName}
                                fill={yLeftColor}
                                radius={[4, 4, 0, 0]}
                                barSize={30}
                            />
                            <Line
                                yAxisId="right"
                                type="monotone"
                                dataKey={yRightKey}
                                name={yRightName}
                                stroke={yRightColor}
                                strokeWidth={2}
                                dot={{ fill: yRightColor, r: 3 }}
                            />
                        </ComposedChart>
                    </ResponsiveContainer>
                ) : (
                    <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
                        No data available
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
