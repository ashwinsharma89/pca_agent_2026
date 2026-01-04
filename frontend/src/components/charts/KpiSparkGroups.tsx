"use client";

import React from 'react';
import { Card, CardContent } from "@/components/ui/card";
import { TrendingUp, TrendingDown } from 'lucide-react';

interface KpiData {
    spend?: number;
    impressions?: number;
    clicks?: number;
    conversions?: number;
    cpm?: number;
    cpc?: number;
    cpa?: number;
    roas?: number;
    ctr?: number;
    reach?: number;
    [key: string]: number | undefined;  // Allow extra metrics
}

interface SchemaMetrics {
    spend?: boolean;
    impressions?: boolean;
    clicks?: boolean;
    conversions?: boolean;
    reach?: boolean;
    ctr?: boolean;
    cpc?: boolean;
    cpa?: boolean;
    cpm?: boolean;
    roas?: boolean;
    [key: string]: boolean | undefined;
}

interface KpiSparkGroupsProps {
    data: {
        current: KpiData;
        previous: KpiData;
        sparkline: Record<string, any>[];
    };
    schema?: {
        metrics?: SchemaMetrics;
        extra_metrics?: string[];
    };
}

export function KpiSparkGroups({ data, schema }: KpiSparkGroupsProps) {
    if (!data || !data.current) return null;

    const { current, previous } = data;
    const metrics = schema?.metrics || {};
    const extraMetrics = schema?.extra_metrics || [];

    // Format large numbers as M or K
    const formatNumber = (num: number | undefined) => {
        if (num === undefined || num === null) return '0';
        if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
        if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
        return num.toLocaleString();
    };

    const calculateChange = (curr: number | undefined, prev: number | undefined) => {
        if (!prev || prev === 0) return 0;
        if (curr === undefined) return 0;
        return ((curr - prev) / prev) * 100;
    };

    const formatPercent = (val: number) => {
        const absVal = Math.abs(val).toFixed(0);
        return `${val >= 0 ? '' : '-'}${absVal}%`;
    };

    const MetricItem = ({ label, value, color }: { label: string; value: string | number; color?: string }) => (
        <div className="flex flex-col items-center flex-1">
            <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium mb-1">{label}</span>
            <span className={`text-xl font-bold ${color || 'text-foreground'}`}>{value}</span>
        </div>
    );

    const ChangeIndicator = ({ val }: { val: number }) => null; // Hidden for now as per user request

    // Dynamically build KPI groups based on available metrics
    const kpiGroups: {
        title: string;
        color: string;
        metrics: { label: string; value: string }[];
        changes: number[];
        show: boolean;
    }[] = [];

    // Spend & Impressions Group (show if spend OR impressions available)
    if (metrics.spend || metrics.impressions) {
        const groupMetrics: { label: string; value: string }[] = [];
        const groupChanges: number[] = [];

        if (metrics.spend) {
            groupMetrics.push({ label: "Cost", value: `$${formatNumber(current.spend)}` });
            groupChanges.push(calculateChange(current.spend, previous.spend));
        }
        if (metrics.cpm) {
            groupMetrics.push({ label: "CPM", value: `$${(current.cpm ?? 0).toFixed(2)}` });
            groupChanges.push(calculateChange(current.cpm, previous.cpm));
        }
        if (metrics.impressions) {
            groupMetrics.push({ label: "Impressions", value: formatNumber(current.impressions) });
            groupChanges.push(calculateChange(current.impressions, previous.impressions));
        }
        if (metrics.reach) {
            groupMetrics.push({ label: "Reach", value: formatNumber(current.reach) });
            groupChanges.push(calculateChange(current.reach, previous.reach));
        }

        if (groupMetrics.length > 0) {
            kpiGroups.push({
                title: "Spend & Impressions",
                color: "bg-emerald-500",
                metrics: groupMetrics,
                changes: groupChanges,
                show: true
            });
        }
    }

    // Clicks Group (show if clicks available)
    if (metrics.clicks) {
        const groupMetrics: { label: string; value: string }[] = [];
        const groupChanges: number[] = [];

        groupMetrics.push({ label: "Clicks", value: formatNumber(current.clicks) });
        groupChanges.push(calculateChange(current.clicks, previous.clicks));

        if (metrics.ctr) {
            groupMetrics.push({ label: "CTR", value: `${(current.ctr ?? 0).toFixed(2)}%` });
            groupChanges.push(calculateChange(current.ctr, previous.ctr));
        }
        if (metrics.cpc) {
            groupMetrics.push({ label: "CPC", value: `$${(current.cpc ?? 0).toFixed(2)}` });
            groupChanges.push(calculateChange(current.cpc, previous.cpc));
        }

        kpiGroups.push({
            title: "Clicks",
            color: "bg-amber-500",
            metrics: groupMetrics,
            changes: groupChanges,
            show: true
        });
    }

    // Conversions Group (show if conversions available)
    if (metrics.conversions) {
        const groupMetrics: { label: string; value: string }[] = [];
        const groupChanges: number[] = [];

        groupMetrics.push({ label: "Conversions", value: formatNumber(current.conversions) });
        groupChanges.push(calculateChange(current.conversions, previous.conversions));

        // Conversion rate (needs clicks too)
        if (metrics.clicks && current.clicks) {
            const convRate = ((current.conversions ?? 0) / Math.max(1, current.clicks)) * 100;
            const prevConvRate = ((previous.conversions ?? 0) / Math.max(1, previous.clicks ?? 1)) * 100;
            groupMetrics.push({ label: "Conv Rate", value: `${convRate.toFixed(2)}%` });
            groupChanges.push(calculateChange(convRate, prevConvRate));
        }

        if (metrics.cpa) {
            groupMetrics.push({ label: "CPA", value: `$${(current.cpa ?? 0).toFixed(2)}` });
            groupChanges.push(calculateChange(current.cpa, previous.cpa));
        }
        if (metrics.roas) {
            groupMetrics.push({ label: "ROAS", value: `${(current.roas ?? 0).toFixed(2)}x` });
            groupChanges.push(calculateChange(current.roas, previous.roas));
        }

        kpiGroups.push({
            title: "Conversions",
            color: "bg-blue-500",
            metrics: groupMetrics,
            changes: groupChanges,
            show: true
        });
    }

    // Extra Metrics Group (if any extra numeric columns exist)
    if (extraMetrics.length > 0) {
        const groupMetrics: { label: string; value: string }[] = [];
        const groupChanges: number[] = [];

        for (const key of extraMetrics) {
            const currVal = current[key];
            const prevVal = previous[key];
            if (currVal !== undefined) {
                // Format label nicely (video_starts -> Video Starts)
                const label = key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                groupMetrics.push({ label, value: formatNumber(currVal) });
                groupChanges.push(calculateChange(currVal, prevVal));
            }
        }

        if (groupMetrics.length > 0) {
            kpiGroups.push({
                title: "Additional Metrics",
                color: "bg-purple-500",
                metrics: groupMetrics,
                changes: groupChanges,
                show: true
            });
        }
    }

    // If no schema provided, fall back to old behavior (show all 3 groups)
    if (!schema || Object.keys(metrics).length === 0) {
        return (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Spend & Impressions */}
                <Card className="overflow-hidden border-none bg-background/50 backdrop-blur-sm shadow-lg ring-1 ring-white/10">
                    <div className="bg-emerald-500 py-2 px-4">
                        <span className="text-white text-xs font-bold uppercase tracking-widest">Spend & Impressions</span>
                    </div>
                    <CardContent className="p-6">
                        <div className="flex justify-between items-start">
                            <div className="flex flex-col items-center flex-1">
                                <MetricItem label="Cost" value={`$${formatNumber(current.spend)}`} />
                                <div className="mt-1">
                                    <ChangeIndicator val={calculateChange(current.spend, previous.spend)} />
                                </div>
                            </div>
                            <div className="flex flex-col items-center flex-1">
                                <MetricItem label="CPM" value={`$${(current.cpm ?? 0).toFixed(2)}`} />
                                <div className="mt-1">
                                    <ChangeIndicator val={calculateChange(current.cpm, previous.cpm)} />
                                </div>
                            </div>
                            <div className="flex flex-col items-center flex-1">
                                <MetricItem label="Impressions" value={formatNumber(current.impressions)} />
                                <div className="mt-1">
                                    <ChangeIndicator val={calculateChange(current.impressions, previous.impressions)} />
                                </div>
                            </div>
                            <div className="flex flex-col items-center flex-1">
                                <MetricItem label="Reach" value={formatNumber(current.reach)} />
                                <div className="mt-1">
                                    <ChangeIndicator val={calculateChange(current.reach, previous.reach)} />
                                </div>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* Clicks */}
                <Card className="overflow-hidden border-none bg-background/50 backdrop-blur-sm shadow-lg ring-1 ring-white/10">
                    <div className="bg-amber-500 py-2 px-4">
                        <span className="text-white text-xs font-bold uppercase tracking-widest">Clicks</span>
                    </div>
                    <CardContent className="p-6">
                        <div className="flex justify-between items-start">
                            <div className="flex flex-col items-center flex-1">
                                <MetricItem label="Clicks" value={formatNumber(current.clicks)} />
                                <div className="mt-1">
                                    <ChangeIndicator val={calculateChange(current.clicks, previous.clicks)} />
                                </div>
                            </div>
                            <div className="flex flex-col items-center flex-1">
                                <MetricItem label="CTR" value={`${(current.ctr ?? 0).toFixed(2)}%`} />
                                <div className="mt-1">
                                    <ChangeIndicator val={calculateChange(current.ctr, previous.ctr)} />
                                </div>
                            </div>
                            <div className="flex flex-col items-center flex-1">
                                <MetricItem label="CPC" value={`$${(current.cpc ?? 0).toFixed(2)}`} />
                                <div className="mt-1">
                                    <ChangeIndicator val={calculateChange(current.cpc, previous.cpc)} />
                                </div>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* Conversions */}
                <Card className="overflow-hidden border-none bg-background/50 backdrop-blur-sm shadow-lg ring-1 ring-white/10">
                    <div className="bg-blue-500 py-2 px-4">
                        <span className="text-white text-xs font-bold uppercase tracking-widest">Conversions</span>
                    </div>
                    <CardContent className="p-6">
                        <div className="flex justify-between items-start">
                            <div className="flex flex-col items-center flex-1">
                                <MetricItem label="Conversions" value={formatNumber(current.conversions)} />
                                <div className="mt-1">
                                    <ChangeIndicator val={calculateChange(current.conversions, previous.conversions)} />
                                </div>
                            </div>
                            <div className="flex flex-col items-center flex-1">
                                <MetricItem label="CPA" value={`$${(current.cpa ?? 0).toFixed(2)}`} />
                                <div className="mt-1">
                                    <ChangeIndicator val={calculateChange(current.cpa, previous.cpa)} />
                                </div>
                            </div>
                            <div className="flex flex-col items-center flex-1">
                                <MetricItem label="ROAS" value={`${(current.roas ?? 0).toFixed(2)}x`} />
                                <div className="mt-1">
                                    <ChangeIndicator val={calculateChange(current.roas, previous.roas)} />
                                </div>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>
        );
    }

    // Dynamic grid columns based on number of groups
    const gridCols = kpiGroups.length === 1 ? 'md:grid-cols-1' :
        kpiGroups.length === 2 ? 'md:grid-cols-2' :
            kpiGroups.length >= 3 ? 'md:grid-cols-3' : 'md:grid-cols-4';

    return (
        <div className={`grid grid-cols-1 ${gridCols} gap-6`}>
            {kpiGroups.map((group, idx) => (
                <Card key={idx} className="overflow-hidden border-none bg-background/50 backdrop-blur-sm shadow-lg ring-1 ring-white/10">
                    <div className={`${group.color} py-2 px-4`}>
                        <span className="text-white text-xs font-bold uppercase tracking-widest">{group.title}</span>
                    </div>
                    <CardContent className="p-6">
                        <div className="flex justify-between items-start">
                            {group.metrics.map((m, i) => (
                                <div key={i} className="flex flex-col items-center flex-1">
                                    <MetricItem label={m.label} value={m.value} />
                                    <div className="mt-1">
                                        <ChangeIndicator val={group.changes[i]} />
                                    </div>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            ))}
        </div>
    );
}
