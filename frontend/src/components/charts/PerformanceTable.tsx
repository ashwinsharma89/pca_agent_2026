"use client";

import React, { useState, useMemo } from 'react';
import { ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { List } from 'react-window';
import { AutoSizer } from 'react-virtualized-auto-sizer';

interface PerformanceTableProps {
    title: string;
    description: string;
    data: any[];
    type: 'month' | 'platform' | 'channel' | 'funnel' | 'region' | 'audience' | 'age' | 'ad_type' | 'objective' | 'targeting' | 'device';
    onMonthClick?: (month: string) => void;
    selectedMonth?: string | null;
    onPlatformClick?: (platform: string) => void;
    selectedPlatform?: string | null;
    onChannelClick?: (channel: string) => void;
    selectedChannel?: string | null;
    onFunnelStageClick?: (funnelStage: string) => void;
    selectedFunnelStage?: string | null;
    // Generic click handler for new dimensions if needed in future
    onDimensionClick?: (value: string) => void;
    selectedDimension?: string | null;
    schema?: {
        metrics?: Record<string, boolean>;
    };
}

export function PerformanceTable({
    title, description, data, type,
    onMonthClick, selectedMonth,
    onPlatformClick, selectedPlatform,
    onChannelClick, selectedChannel,
    onFunnelStageClick, selectedFunnelStage,
    onDimensionClick, selectedDimension,
    schema
}: PerformanceTableProps) {
    const [sortKey, setSortKey] = useState<string | null>(null);
    const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

    // Determine primary dimension key and label
    const getPrimaryDimension = (t: string): { key: string; label: string; width?: number } => {
        switch (t) {
            case 'month': return { key: 'month', label: 'Month' };
            case 'platform': return { key: 'platform', label: 'Platform' };
            case 'channel': return { key: 'channel', label: 'Channel' };
            case 'funnel': return { key: 'funnel', label: 'Funnel Stage' };
            case 'region': return { key: 'region', label: 'Region' };
            case 'audience': return { key: 'audience', label: 'Audience' };
            case 'age': return { key: 'age', label: 'Age Group' };
            case 'ad_type': return { key: 'ad_type', label: 'Ad Type' };
            case 'objective': return { key: 'objective', label: 'Objective' };
            case 'targeting': return { key: 'targeting', label: 'Targeting' };
            case 'device': return { key: 'device', label: 'Device' };
            default: return { key: 'name', label: 'Name' };
        }
    };

    const primaryDim = getPrimaryDimension(type);

    // Define all possible columns
    const allColumns: { key: string; label: string; width?: number }[] = [
        primaryDim,
        { key: 'spend', label: 'Spend', width: 100 },
        { key: 'impressions', label: 'Impr.', width: 80 },
        { key: 'clicks', label: 'Clicks', width: 80 },
        { key: 'ctr', label: 'CTR', width: 70 },
        { key: 'conversions', label: 'Conv.', width: 70 },
        { key: 'cpa', label: 'CPA', width: 70 },
        { key: 'roas', label: 'ROAS', width: 70 },
        { key: 'cpc', label: 'CPC', width: 70 },
        { key: 'cpm', label: 'CPM', width: 70 }
    ];

    // Filter columns based on schema availability
    const columns = allColumns.filter(col => {
        // Always show the primary dimension column
        if (col.key === primaryDim.key) return true;
        // If no schema, show all columns (backwards compatibility)
        if (!schema?.metrics) return true;
        // Check if metric is available
        return schema.metrics[col.key] !== false;
    });

    // Sort data
    const sortedData = useMemo(() => {
        if (!data || data.length === 0) return [];
        if (!sortKey) return data;

        return [...data].sort((a, b) => {
            const aVal = a[sortKey];
            const bVal = b[sortKey];

            // Handle string sorting (month, platform)
            if (typeof aVal === 'string' && typeof bVal === 'string') {
                const comparison = aVal.localeCompare(bVal);
                return sortDirection === 'asc' ? comparison : -comparison;
            }

            // Handle number sorting
            const aNum = Number(aVal) || 0;
            const bNum = Number(bVal) || 0;
            return sortDirection === 'asc' ? aNum - bNum : bNum - aNum;
        });
    }, [data, sortKey, sortDirection]);

    if (!data || data.length === 0) return null;

    const formatMonth = (monthStr: string) => {
        const [year, month] = monthStr.split('-');
        const date = new Date(parseInt(year), parseInt(month) - 1);
        const monthName = date.toLocaleDateString('en-US', { month: 'short' });
        const yearShort = year.slice(-2);
        return `${monthName} ${yearShort}`;
    };

    const formatValue = (key: string, val: unknown) => {
        if (key === 'month') return formatMonth(String(val));
        if (key === 'spend') return `$${Number(val).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
        if (key === 'cpm' || key === 'cpc' || key === 'cpa') return `$${Number(val).toFixed(2)}`;
        if (key === 'ctr' || key === 'roas') return `${Number(val).toFixed(2)}${key === 'ctr' ? '%' : 'x'}`;
        if (key === 'impressions' || key === 'clicks' || key === 'conversions' || key === 'reach') return Number(val).toLocaleString();
        return String(val);
    };

    const getHeatmapColor = (key: string, val: number, allData: Record<string, any>[]) => {
        const values = allData.map(d => Number(d[key]));
        const min = Math.min(...values);
        const max = Math.max(...values);
        const range = max - min;
        if (range === 0) return 'rgba(16, 185, 129, 0.1)';

        const percentage = (val - min) / range;
        const opacity = 0.1 + (percentage * 0.4);
        return `rgba(16, 185, 129, ${opacity})`;
    };

    const handleSort = (key: string) => {
        if (sortKey === key) {
            setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
        } else {
            setSortKey(key);
            setSortDirection(key === 'month' || key === 'platform' ? 'asc' : 'desc');
        }
    };

    const getSortIcon = (key: string) => {
        if (sortKey !== key) {
            return <ArrowUpDown className="h-3 w-3 opacity-50" />;
        }
        return sortDirection === 'asc'
            ? <ArrowUp className="h-3 w-3" />
            : <ArrowDown className="h-3 w-3" />;
    };

    const Row = ({ index, style }: { index: number; style: React.CSSProperties }) => {
        const row = sortedData[index];
        const isMonthRow = type === 'month';
        const isPlatformRow = type === 'platform';
        const isChannelRow = type === 'channel';
        const isFunnelRow = type === 'funnel';
        const isGenericRow = !isMonthRow && !isPlatformRow && !isChannelRow && !isFunnelRow;

        const isSelected = (isMonthRow && selectedMonth === row.month)
            || (isPlatformRow && selectedPlatform === row.platform)
            || (isChannelRow && selectedChannel === row.channel)
            || (isFunnelRow && selectedFunnelStage === row.funnel)
            || (isGenericRow && selectedDimension === row[primaryDim.key]);

        const isClickable = (isMonthRow && onMonthClick)
            || (isPlatformRow && onPlatformClick)
            || (isChannelRow && onChannelClick)
            || (isFunnelRow && onFunnelStageClick)
            || (isGenericRow && onDimensionClick);

        return (
            <div
                className={`
                    flex items-center border-b border-white/5 transition-all text-xs
                    ${isClickable ? 'cursor-pointer hover:bg-blue-500/20' : 'hover:bg-white/5'}
                    ${isSelected ? 'bg-blue-500/30' : ''}
                `}
                style={style}
                onClick={() => {
                    if (isMonthRow && onMonthClick) onMonthClick(row.month);
                    else if (isPlatformRow && onPlatformClick) onPlatformClick(row.platform);
                    else if (isChannelRow && onChannelClick) onChannelClick(row.channel);
                    else if (isFunnelRow && onFunnelStageClick) onFunnelStageClick(row.funnel);
                    else if (isGenericRow && onDimensionClick) onDimensionClick(row[primaryDim.key]);
                }}
            >
                {columns.map((col, colIndex) => {
                    const isNumeric = typeof row[col.key] === 'number';
                    const bgColor = isNumeric && col.key !== 'month' && col.key !== 'platform'
                        ? getHeatmapColor(col.key, row[col.key], data)
                        : 'transparent';

                    // Flex grow logic: primary column grows, others fixed width or share space
                    const widthClass = colIndex === 0 ? 'flex-1 min-w-[120px]' : `w-[${col.width || 80}px] shrink-0 text-right`;

                    return (
                        <div
                            key={col.key}
                            className={`px-4 py-2 font-medium truncate ${widthClass} ${isSelected && (['month', 'platform', 'channel'].includes(col.key)) ? 'font-bold text-blue-400' : ''}`}
                            style={colIndex === 0 ? {} : { width: col.width || 80, backgroundColor: bgColor }}
                        >
                            {formatValue(col.key, row[col.key])}
                        </div>
                    );
                })}
            </div>
        );
    };

    return (
        <Card className="border-none bg-background/50 backdrop-blur-sm shadow-lg ring-1 ring-white/10 h-[500px] flex flex-col">
            <CardHeader className="pb-2">
                <CardTitle className="text-sm font-bold uppercase tracking-wider">{title}</CardTitle>
                <CardDescription>{description}</CardDescription>
            </CardHeader>
            <CardContent className="flex-1 min-h-0 p-0 flex flex-col">
                {/* Header Row */}
                <div className="flex items-center px-4 py-2 border-y border-white/10 bg-white/5 font-bold text-[10px] uppercase tracking-tight text-muted-foreground mr-3">
                    {columns.map((col, colIndex) => (
                        <div
                            key={col.key}
                            className={`flex items-center gap-1 cursor-pointer hover:text-white transition-colors ${colIndex === 0 ? 'flex-1 min-w-[120px]' : 'shrink-0 justify-end'}`}
                            style={colIndex === 0 ? {} : { width: col.width || 80 }}
                            onClick={() => handleSort(col.key)}
                        >
                            {col.label}
                            {getSortIcon(col.key)}
                        </div>
                    ))}
                </div>

                {/* Virtualized List */}
                <div className="flex-1">
                    <AutoSizer renderProp={({ height, width }: { height: number | undefined; width: number | undefined }) => {
                        if (typeof height !== 'number' || typeof width !== 'number') return null;

                        return (
                            <List<any>
                                style={{ height, width }}
                                rowCount={sortedData.length}
                                rowHeight={40}
                                rowComponent={Row}
                                rowProps={{}}
                            />
                        );
                    }} />
                </div>
            </CardContent>
        </Card>
    );
}
