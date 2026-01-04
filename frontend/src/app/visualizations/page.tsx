"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Loader2, Filter, RefreshCw } from "lucide-react";
import { DateRangePicker } from "@/components/ui/date-range-picker";
import { DateRange } from "react-day-picker";
import { MultiSelect } from "@/components/ui/multi-select";
import dynamic from 'next/dynamic';

// Dynamically import Recharts to avoid SSR issues
const ResponsiveContainer = dynamic(() => import('recharts').then(mod => mod.ResponsiveContainer), { ssr: false });
const LineChart = dynamic(() => import('recharts').then(mod => mod.LineChart), { ssr: false });
const Line = dynamic(() => import('recharts').then(mod => mod.Line), { ssr: false });
const BarChart = dynamic(() => import('recharts').then(mod => mod.BarChart), { ssr: false });
const Bar = dynamic(() => import('recharts').then(mod => mod.Bar), { ssr: false });
const ComposedChart = dynamic(() => import('recharts').then(mod => mod.ComposedChart), { ssr: false });
const PieChart = dynamic(() => import('recharts').then(mod => mod.PieChart), { ssr: false });
const Pie = dynamic(() => import('recharts').then(mod => mod.Pie), { ssr: false });
const Cell = dynamic(() => import('recharts').then(mod => mod.Cell), { ssr: false });
const XAxis = dynamic(() => import('recharts').then(mod => mod.XAxis), { ssr: false });
const YAxis = dynamic(() => import('recharts').then(mod => mod.YAxis), { ssr: false });
const CartesianGrid = dynamic(() => import('recharts').then(mod => mod.CartesianGrid), { ssr: false });
const Tooltip = dynamic(() => import('recharts').then(mod => mod.Tooltip), { ssr: false });
const Legend = dynamic(() => import('recharts').then(mod => mod.Legend), { ssr: false });
const AreaChart = dynamic(() => import('recharts').then(mod => mod.AreaChart), { ssr: false });
const Area = dynamic(() => import('recharts').then(mod => mod.Area), { ssr: false });
const RadarChart = dynamic(() => import('recharts').then(mod => mod.RadarChart), { ssr: false });
const Radar = dynamic(() => import('recharts').then(mod => mod.Radar), { ssr: false });
const PolarGrid = dynamic(() => import('recharts').then(mod => mod.PolarGrid), { ssr: false });
const PolarAngleAxis = dynamic(() => import('recharts').then(mod => mod.PolarAngleAxis), { ssr: false });
const PolarRadiusAxis = dynamic(() => import('recharts').then(mod => mod.PolarRadiusAxis), { ssr: false });


const COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];
const DEVICE_COLORS = ['#a78bfa', '#c4b5fd', '#ddd6fe', '#e9d5ff', '#f3e8ff', '#fae8ff']; // Subtle purple/lavender tones


interface VisualizationFilters {
    platforms: string[];
    dateRange?: DateRange;
    primaryMetric: 'spend' | 'clicks' | 'conversions' | 'impressions';
    secondaryMetric?: 'spend' | 'clicks' | 'conversions' | 'impressions' | 'none';
    funnelStages: string[];
    channels: string[];
    devices: string[];
    placements: string[];
}

export default function GlobalVisualizationsPage() {
    const [data, setData] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    // Available filter options
    const [availablePlatforms, setAvailablePlatforms] = useState<string[]>([]);
    const [availableFunnelStages, setAvailableFunnelStages] = useState<string[]>([]);
    const [availableChannels, setAvailableChannels] = useState<string[]>([]);
    const [availableDevices, setAvailableDevices] = useState<string[]>([]);
    const [availablePlacements, setAvailablePlacements] = useState<string[]>([]);

    // Filters state
    const [filters, setFilters] = useState<VisualizationFilters>({
        platforms: [],
        primaryMetric: 'spend',
        secondaryMetric: 'clicks',
        funnelStages: [],
        channels: [],
        devices: [],
        placements: []
    });

    // Chart data states
    const [funnelData, setFunnelData] = useState<any[]>([]);
    const [audienceData, setAudienceData] = useState<any[]>([]);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            setLoading(true);

            // Build filter object
            const filterParams: any = {};
            if (filters.platforms.length > 0) {
                filterParams.platforms = filters.platforms.join(',');
            }

            if (filters.dateRange?.from) {
                filterParams.startDate = filters.dateRange.from.toISOString().split('T')[0];
            }

            if (filters.dateRange?.to) {
                filterParams.endDate = filters.dateRange.to.toISOString().split('T')[0];
            }

            filterParams.primaryMetric = filters.primaryMetric;
            if (filters.secondaryMetric && filters.secondaryMetric !== 'none') {
                filterParams.secondaryMetric = filters.secondaryMetric;
            }

            if (filters.funnelStages.length > 0) {
                filterParams.funnelStages = filters.funnelStages.join(',');
            }

            if (filters.channels.length > 0) {
                filterParams.channels = filters.channels.join(',');
            }

            if (filters.devices.length > 0) {
                filterParams.devices = filters.devices.join(',');
            }

            if (filters.placements.length > 0) {
                filterParams.placements = filters.placements.join(',');
            }

            const result: any = await api.getGlobalVisualizations(filterParams);
            setData(result);

            // Extract platforms from visualization data (already aggregated by backend)
            if (result?.platform) {
                const platforms = result.platform.map((p: any) => p.name).filter((v: string) => v && v !== 'Unknown');
                setAvailablePlatforms(platforms);
            }

            // Extract channels from visualization data (already aggregated by backend)
            if (result?.channel) {
                const channels = result.channel.map((c: any) => c.name).filter((v: string) => v && v !== 'Unknown');
                setAvailableChannels(channels);

            }

            // Fetch filter options from dedicated endpoint (avoids NaN serialization issues)
            try {
                const filterOptions: any = await api.get('/campaigns/filters');

                // Set all available filter options
                if (filterOptions.platforms?.length > 0 && !result?.platform) {
                    setAvailablePlatforms(filterOptions.platforms);
                }
                if (filterOptions.channels?.length > 0 && (!result?.channel || result.channel.length === 0)) {
                    setAvailableChannels(filterOptions.channels);
                }
                if (filterOptions.funnel_stages?.length > 0) {
                    setAvailableFunnelStages(filterOptions.funnel_stages);
                }
                if (filterOptions.devices?.length > 0) {
                    setAvailableDevices(filterOptions.devices);
                }
                if (filterOptions.placements?.length > 0) {
                    setAvailablePlacements(filterOptions.placements);
                }
            } catch (filterError) {
                console.warn("Failed to load filter options:", filterError);
                // Filters will remain empty but page still works
            }

            // Generate funnel and audience data
            generateFunnelData();
            generateAudienceData();
        } catch (error) {
            console.error("Failed to load visualizations", error);
        } finally {
            setLoading(false);
        }
    };

    const generateFunnelData = async () => {
        try {
            // Use dedicated endpoint for production-grade NaN-safe data
            const funnelStats: any = await api.get('/campaigns/funnel-stats');

            if (funnelStats?.data && funnelStats.data.length > 0) {
                setFunnelData(funnelStats.data);
            }
        } catch (error) {
            console.warn("Failed to generate funnel data:", error);
            // Chart will show "No data" message gracefully
        }
    };

    const generateAudienceData = async () => {
        try {
            // Use dedicated endpoint for production-grade NaN-safe data
            const audienceStats: any = await api.get('/campaigns/audience-stats');

            if (audienceStats?.data && audienceStats.data.length > 0) {
                setAudienceData(audienceStats.data);
            }
        } catch (error) {
            console.warn("Failed to generate audience data:", error);
            // Chart will show "No data" message gracefully
        }
    };

    const applyFilters = () => {
        fetchData();
    };

    if (loading) {
        return (
            <div className="flex h-screen items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin" />
            </div>
        );
    }

    if (!data) {
        return <div className="p-8">No data available.</div>;
    }

    const platformOptions = availablePlatforms.map(p => ({ label: p, value: p }));
    const funnelOptions = availableFunnelStages.map(f => ({ label: f, value: f }));
    const channelOptions = availableChannels.map(c => ({ label: c, value: c }));
    const deviceOptions = availableDevices.map(d => ({ label: d, value: d }));
    const placementOptions = availablePlacements.map(p => ({ label: p, value: p }));

    return (
        <div className="container mx-auto py-10 space-y-8">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">📊 Global Visualizations</h1>
                <p className="text-muted-foreground">
                    Deep dive into performance metrics across all campaigns and platforms.
                </p>
            </div>

            {/* Enhanced Filters Section */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Filter className="h-5 w-5" />
                        Filters
                    </CardTitle>
                    <CardDescription>Refine your visualization data</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="grid gap-6">
                        {/* Row 1: Platform, Date Range, Primary Metric, Secondary Metric */}
                        <div className="grid gap-4 md:grid-cols-4">
                            <div className="space-y-2">
                                <Label>Platform</Label>
                                <MultiSelect
                                    options={platformOptions}
                                    selected={filters.platforms}
                                    onChange={(selected) => setFilters({ ...filters, platforms: selected })}
                                    placeholder="All Platforms"
                                />
                            </div>

                            <div className="space-y-2">
                                <Label>Date Range</Label>
                                <DateRangePicker
                                    date={filters.dateRange}
                                    onDateChange={(range) => setFilters({ ...filters, dateRange: range })}
                                />
                            </div>

                            <div className="space-y-2">
                                <Label>Primary Metric</Label>
                                <Select value={filters.primaryMetric} onValueChange={(value: any) => setFilters({ ...filters, primaryMetric: value })}>
                                    <SelectTrigger>
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="spend">Spend</SelectItem>
                                        <SelectItem value="clicks">Clicks</SelectItem>
                                        <SelectItem value="conversions">Conversions</SelectItem>
                                        <SelectItem value="impressions">Impressions</SelectItem>
                                        <SelectItem value="ctr">CTR (%)</SelectItem>
                                        <SelectItem value="cpc">CPC ($)</SelectItem>
                                        <SelectItem value="cpa">CPA ($)</SelectItem>
                                        <SelectItem value="roas">ROAS</SelectItem>
                                        <SelectItem value="cpm">CPM ($)</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="space-y-2">
                                <Label>Secondary Metric</Label>
                                <Select value={filters.secondaryMetric || 'none'} onValueChange={(value: any) => setFilters({ ...filters, secondaryMetric: value })}>
                                    <SelectTrigger>
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="none">None</SelectItem>
                                        <SelectItem value="spend">Spend</SelectItem>
                                        <SelectItem value="clicks">Clicks</SelectItem>
                                        <SelectItem value="conversions">Conversions</SelectItem>
                                        <SelectItem value="impressions">Impressions</SelectItem>
                                        <SelectItem value="ctr">CTR (%)</SelectItem>
                                        <SelectItem value="cpc">CPC ($)</SelectItem>
                                        <SelectItem value="cpa">CPA ($)</SelectItem>
                                        <SelectItem value="roas">ROAS</SelectItem>
                                        <SelectItem value="cpm">CPM ($)</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>

                        {/* Row 2: Funnel, Channel, Device, Placement */}
                        <div className="grid gap-4 md:grid-cols-4">
                            <div className="space-y-2">
                                <Label>Funnel Stage</Label>
                                <MultiSelect
                                    options={funnelOptions}
                                    selected={filters.funnelStages}
                                    onChange={(selected) => setFilters({ ...filters, funnelStages: selected })}
                                    placeholder="All Stages"
                                />
                            </div>

                            <div className="space-y-2">
                                <Label>Channel</Label>
                                <MultiSelect
                                    options={channelOptions}
                                    selected={filters.channels}
                                    onChange={(selected) => setFilters({ ...filters, channels: selected })}
                                    placeholder="All Channels"
                                />
                            </div>

                            <div className="space-y-2">
                                <Label>Device</Label>
                                <MultiSelect
                                    options={deviceOptions}
                                    selected={filters.devices}
                                    onChange={(selected) => setFilters({ ...filters, devices: selected })}
                                    placeholder="All Devices"
                                />
                            </div>

                            <div className="space-y-2">
                                <Label>Placement</Label>
                                <MultiSelect
                                    options={placementOptions}
                                    selected={filters.placements}
                                    onChange={(selected) => setFilters({ ...filters, placements: selected })}
                                    placeholder="All Placements"
                                />
                            </div>
                        </div>

                        {/* Apply Button */}
                        <div className="flex justify-end">
                            <Button onClick={applyFilters} className="w-full md:w-auto">
                                <RefreshCw className="mr-2 h-4 w-4" />
                                Apply Filters
                            </Button>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Main Trend Chart */}
            <Card>
                <CardHeader>
                    <CardTitle>📈 Performance Trends</CardTitle>
                    <CardDescription>
                        {filters.primaryMetric.charAt(0).toUpperCase() + filters.primaryMetric.slice(1)}
                        {filters.secondaryMetric && filters.secondaryMetric !== 'none' &&
                            ` and ${filters.secondaryMetric.charAt(0).toUpperCase() + filters.secondaryMetric.slice(1)}`
                        } over time
                    </CardDescription>
                </CardHeader>
                <CardContent className="h-[400px]">
                    <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={data.trend}>
                            <defs>
                                <linearGradient id="colorPrimary" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.8} />
                                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                                </linearGradient>
                                <linearGradient id="colorSecondary" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#22c55e" stopOpacity={0.8} />
                                    <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                            <XAxis dataKey="date" className="text-xs" />
                            <YAxis yAxisId="left" className="text-xs" />
                            {filters.secondaryMetric && filters.secondaryMetric !== 'none' && (
                                <YAxis yAxisId="right" orientation="right" className="text-xs" />
                            )}
                            <Tooltip
                                contentStyle={{ backgroundColor: 'var(--background)', borderColor: 'var(--border)' }}
                                itemStyle={{ color: 'var(--foreground)' }}
                            />
                            <Legend />
                            <Area
                                yAxisId="left"
                                type="monotone"
                                dataKey={filters.primaryMetric}
                                stroke="#6366f1"
                                fillOpacity={1}
                                fill="url(#colorPrimary)"
                                name={filters.primaryMetric.charAt(0).toUpperCase() + filters.primaryMetric.slice(1)}
                            />
                            {filters.secondaryMetric && filters.secondaryMetric !== 'none' && (
                                <Area
                                    yAxisId="right"
                                    type="monotone"
                                    dataKey={filters.secondaryMetric}
                                    stroke="#22c55e"
                                    fillOpacity={1}
                                    fill="url(#colorSecondary)"
                                    name={filters.secondaryMetric.charAt(0).toUpperCase() + filters.secondaryMetric.slice(1)}
                                />
                            )}
                        </AreaChart>
                    </ResponsiveContainer>
                </CardContent>
            </Card>

            <div className="grid gap-6 md:grid-cols-2">
                {/* Platform Performance */}
                <Card>
                    <CardHeader>
                        <CardTitle>🎯 Platform Performance</CardTitle>
                        <CardDescription>Spend vs Conversions by Ad Platform.</CardDescription>
                    </CardHeader>
                    <CardContent className="h-[350px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={data.platform} layout="vertical">
                                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                                <XAxis type="number" className="text-xs" />
                                <YAxis dataKey="name" type="category" className="text-xs" width={80} />
                                <Tooltip
                                    contentStyle={{ backgroundColor: 'var(--background)', borderColor: 'var(--border)' }}
                                    itemStyle={{ color: 'var(--foreground)' }}
                                />
                                <Legend />
                                <Bar dataKey="spend" fill="#6366f1" name="Spend ($)" radius={[0, 4, 4, 0]} />
                                <Bar dataKey="conversions" fill="#22c55e" name="Conversions" radius={[0, 4, 4, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    </CardContent>
                </Card>

                {/* Funnel Stage Performance */}
                <Card>
                    <CardHeader>
                        <CardTitle>🔄 Funnel Stage Performance</CardTitle>
                        <CardDescription>Spend, Conversions, and CTR by funnel stage.</CardDescription>
                    </CardHeader>
                    <CardContent className="h-[350px]">
                        {funnelData.length > 0 ? (
                            <ResponsiveContainer width="100%" height="100%">
                                <ComposedChart data={funnelData}>
                                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                                    <XAxis dataKey="stage" className="text-xs" />
                                    <YAxis yAxisId="left" className="text-xs" label={{ value: 'Spend ($) / Conversions', angle: -90, position: 'insideLeft' }} />
                                    <YAxis yAxisId="right" orientation="right" className="text-xs" label={{ value: 'CTR (%)', angle: 90, position: 'insideRight' }} />
                                    <Tooltip
                                        contentStyle={{ backgroundColor: 'var(--background)', borderColor: 'var(--border)' }}
                                    />
                                    <Legend />
                                    <Bar yAxisId="left" dataKey="spend" fill="#22c55e" name="Spend ($)" />
                                    <Bar yAxisId="left" dataKey="conversions" fill="#6366f1" name="Conversions" />
                                    <Line yAxisId="right" type="monotone" dataKey="ctr" stroke="#8b5cf6" strokeWidth={3} name="CTR (%)" dot={{ fill: '#8b5cf6', r: 5 }} />
                                </ComposedChart>
                            </ResponsiveContainer>
                        ) : (
                            <div className="flex items-center justify-center h-full text-muted-foreground">
                                No funnel data available
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>

            <div className="grid gap-6 md:grid-cols-2">
                {/* Audience Analysis */}
                <Card>
                    <CardHeader>
                        <CardTitle>👥 Audience Analysis</CardTitle>
                        <CardDescription>Performance breakdown by audience segment.</CardDescription>
                    </CardHeader>
                    <CardContent className="h-[350px]">
                        {audienceData.length > 0 ? (
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={audienceData}>
                                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                                    <XAxis dataKey="name" className="text-xs" angle={-45} textAnchor="end" height={80} />
                                    <YAxis className="text-xs" />
                                    <Tooltip
                                        contentStyle={{ backgroundColor: 'var(--background)', borderColor: 'var(--border)' }}
                                    />
                                    <Legend />
                                    <Bar dataKey="spend" fill="#6366f1" name="Spend ($)" />
                                    <Bar dataKey="conversions" fill="#22c55e" name="Conversions" />
                                </BarChart>
                            </ResponsiveContainer>
                        ) : (
                            <div className="flex items-center justify-center h-full text-muted-foreground">
                                No audience data available
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Device Breakdown */}
                <Card>
                    <CardHeader>
                        <CardTitle>📱 Device Breakdown</CardTitle>
                        <CardDescription>Traffic distribution by device type.</CardDescription>
                    </CardHeader>
                    <CardContent className="h-[350px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={data.device}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={60}
                                    outerRadius={100}
                                    fill="#8884d8"
                                    paddingAngle={5}
                                    dataKey="value"
                                    label={({ name, percent }) => `${name}: ${((percent || 0) * 100).toFixed(0)}%`}
                                >
                                    {data.device.map((entry: any, index: number) => {
                                        const subtleColors = ['#94a3b8', '#f59e0b', '#10b981'];
                                        return <Cell key={`cell-${index}`} fill={subtleColors[index % subtleColors.length]} />;
                                    })}
                                </Pie>
                                <Tooltip
                                    contentStyle={{ backgroundColor: 'var(--background)', borderColor: 'var(--border)' }}
                                    itemStyle={{ color: 'var(--foreground)' }}
                                />
                                <Legend />
                            </PieChart>
                        </ResponsiveContainer>
                    </CardContent>
                </Card>
            </div>

            {/* New Charts Row 1: Impressions & CPM, Clicks & CPC */}
            <div className="grid gap-6 md:grid-cols-2">
                {/* Impressions & CPM */}
                <Card>
                    <CardHeader>
                        <CardTitle>👁️ Impressions & CPM</CardTitle>
                        <CardDescription>Impressions volume with Cost Per Mille trend.</CardDescription>
                    </CardHeader>
                    <CardContent className="h-[350px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <ComposedChart data={data.platform}>
                                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                                <XAxis dataKey="name" className="text-xs" />
                                <YAxis yAxisId="left" className="text-xs" label={{ value: 'Impressions', angle: -90, position: 'insideLeft' }} />
                                <YAxis yAxisId="right" orientation="right" className="text-xs" label={{ value: 'CPM ($)', angle: 90, position: 'insideRight' }} />
                                <Tooltip contentStyle={{ backgroundColor: 'var(--background)', borderColor: 'var(--border)' }} />
                                <Legend />
                                <Bar yAxisId="left" dataKey="impressions" fill="#3b82f6" name="Impressions" />
                                <Line yAxisId="right" type="monotone" dataKey="cpm" stroke="#f97316" strokeWidth={3} name="CPM ($)" dot={{ fill: '#f97316', r: 5 }} />
                            </ComposedChart>
                        </ResponsiveContainer>
                    </CardContent>
                </Card>

                {/* Clicks & CPC */}
                <Card>
                    <CardHeader>
                        <CardTitle>🖱️ Clicks & CPC</CardTitle>
                        <CardDescription>Click volume with Cost Per Click trend.</CardDescription>
                    </CardHeader>
                    <CardContent className="h-[350px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <ComposedChart data={data.platform}>
                                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                                <XAxis dataKey="name" className="text-xs" />
                                <YAxis yAxisId="left" className="text-xs" label={{ value: 'Clicks', angle: -90, position: 'insideLeft' }} />
                                <YAxis yAxisId="right" orientation="right" className="text-xs" label={{ value: 'CPC ($)', angle: 90, position: 'insideRight' }} />
                                <Tooltip contentStyle={{ backgroundColor: 'var(--background)', borderColor: 'var(--border)' }} />
                                <Legend />
                                <Bar yAxisId="left" dataKey="clicks" fill="#10b981" name="Clicks" />
                                <Line yAxisId="right" type="monotone" dataKey="cpc" stroke="#a855f7" strokeWidth={3} name="CPC ($)" dot={{ fill: '#a855f7', r: 5 }} />
                            </ComposedChart>
                        </ResponsiveContainer>
                    </CardContent>
                </Card>
            </div>

            {/* New Charts Row 2: Conversions & CPA, Performance Funnel */}
            <div className="grid gap-6 md:grid-cols-2">
                {/* Conversions & CPA */}
                <Card>
                    <CardHeader>
                        <CardTitle>🎯 Conversions & CPA</CardTitle>
                        <CardDescription>Conversion volume with Cost Per Acquisition trend.</CardDescription>
                    </CardHeader>
                    <CardContent className="h-[350px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <ComposedChart data={data.platform}>
                                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                                <XAxis dataKey="name" className="text-xs" />
                                <YAxis yAxisId="left" className="text-xs" label={{ value: 'Conversions', angle: -90, position: 'insideLeft' }} />
                                <YAxis yAxisId="right" orientation="right" className="text-xs" label={{ value: 'CPA ($)', angle: 90, position: 'insideRight' }} />
                                <Tooltip contentStyle={{ backgroundColor: 'var(--background)', borderColor: 'var(--border)' }} />
                                <Legend />
                                <Bar yAxisId="left" dataKey="conversions" fill="#f43f5e" name="Conversions" />
                                <Line yAxisId="right" type="monotone" dataKey="cpa" stroke="#14b8a6" strokeWidth={3} name="CPA ($)" dot={{ fill: '#14b8a6', r: 5 }} />
                            </ComposedChart>
                        </ResponsiveContainer>
                    </CardContent>
                </Card>

                {/* Performance Funnel: Spend & Revenue */}
                <Card>
                    <CardHeader>
                        <CardTitle>💰 Spend vs Revenue</CardTitle>
                        <CardDescription>Investment and returns by platform.</CardDescription>
                    </CardHeader>
                    <CardContent className="h-[350px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <ComposedChart data={data.platform}>
                                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                                <XAxis dataKey="name" className="text-xs" />
                                <YAxis yAxisId="left" className="text-xs" label={{ value: 'Amount ($)', angle: -90, position: 'insideLeft' }} />
                                <YAxis yAxisId="right" orientation="right" className="text-xs" label={{ value: 'ROAS', angle: 90, position: 'insideRight' }} />
                                <Tooltip contentStyle={{ backgroundColor: 'var(--background)', borderColor: 'var(--border)' }} />
                                <Legend />
                                <Bar yAxisId="left" dataKey="spend" fill="#f59e0b" name="Spend ($)" />
                                <Bar yAxisId="left" dataKey="revenue" fill="#10b981" name="Revenue ($)" />
                                <Line yAxisId="right" type="monotone" dataKey="roas" stroke="#6366f1" strokeWidth={3} name="ROAS" dot={{ fill: '#6366f1', r: 5 }} />
                            </ComposedChart>
                        </ResponsiveContainer>
                    </CardContent>
                </Card>
            </div>

            {/* Channel-Level Charts */}
            <div className="mt-6">
                <h2 className="text-2xl font-bold mb-4">📊 Channel Performance</h2>
            </div>

            {/* Channel Charts Row 1: Performance & Efficiency */}
            <div className="grid gap-6 md:grid-cols-2">
                {/* Channel Performance Overview */}
                <Card>
                    <CardHeader>
                        <CardTitle>📈 Channel Performance</CardTitle>
                        <CardDescription>Spend and conversions by marketing channel.</CardDescription>
                    </CardHeader>
                    <CardContent className="h-[350px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <ComposedChart data={data.channel || []}>
                                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                                <XAxis dataKey="name" className="text-xs" />
                                <YAxis yAxisId="left" className="text-xs" label={{ value: 'Spend ($)', angle: -90, position: 'insideLeft' }} />
                                <YAxis yAxisId="right" orientation="right" className="text-xs" label={{ value: 'Conversions', angle: 90, position: 'insideRight' }} />
                                <Tooltip contentStyle={{ backgroundColor: 'var(--background)', borderColor: 'var(--border)' }} />
                                <Legend />
                                <Bar yAxisId="left" dataKey="spend" fill="#f59e0b" name="Spend ($)" />
                                <Line yAxisId="right" type="monotone" dataKey="conversions" stroke="#f43f5e" strokeWidth={3} name="Conversions" dot={{ fill: '#f43f5e', r: 5 }} />
                            </ComposedChart>
                        </ResponsiveContainer>
                    </CardContent>
                </Card>

                {/* Channel Efficiency */}
                <Card>
                    <CardHeader>
                        <CardTitle>⚡ Channel Efficiency</CardTitle>
                        <CardDescription>CTR and CPC by marketing channel.</CardDescription>
                    </CardHeader>
                    <CardContent className="h-[350px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <ComposedChart data={data.channel || []}>
                                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                                <XAxis dataKey="name" className="text-xs" />
                                <YAxis yAxisId="left" className="text-xs" label={{ value: 'CTR (%)', angle: -90, position: 'insideLeft' }} />
                                <YAxis yAxisId="right" orientation="right" className="text-xs" label={{ value: 'CPC ($)', angle: 90, position: 'insideRight' }} />
                                <Tooltip contentStyle={{ backgroundColor: 'var(--background)', borderColor: 'var(--border)' }} />
                                <Legend />
                                <Bar yAxisId="left" dataKey="ctr" fill="#10b981" name="CTR (%)" />
                                <Line yAxisId="right" type="monotone" dataKey="cpc" stroke="#a855f7" strokeWidth={3} name="CPC ($)" dot={{ fill: '#a855f7', r: 5 }} />
                            </ComposedChart>
                        </ResponsiveContainer>
                    </CardContent>
                </Card>
            </div>

            {/* Channel Charts Row 2: ROI */}
            <div className="grid gap-6 md:grid-cols-2">
                {/* Channel ROI */}
                <Card>
                    <CardHeader>
                        <CardTitle>💎 Channel ROI</CardTitle>
                        <CardDescription>Cost per acquisition and return on ad spend by channel.</CardDescription>
                    </CardHeader>
                    <CardContent className="h-[350px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <ComposedChart data={data.channel || []}>
                                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                                <XAxis dataKey="name" className="text-xs" />
                                <YAxis yAxisId="left" className="text-xs" label={{ value: 'CPA ($)', angle: -90, position: 'insideLeft' }} />
                                <YAxis yAxisId="right" orientation="right" className="text-xs" label={{ value: 'ROAS', angle: 90, position: 'insideRight' }} />
                                <Tooltip contentStyle={{ backgroundColor: 'var(--background)', borderColor: 'var(--border)' }} />
                                <Legend />
                                <Bar yAxisId="left" dataKey="cpa" fill="#14b8a6" name="CPA ($)" />
                                <Line yAxisId="right" type="monotone" dataKey="roas" stroke="#6366f1" strokeWidth={3} name="ROAS" dot={{ fill: '#6366f1', r: 5 }} />
                            </ComposedChart>
                        </ResponsiveContainer>
                    </CardContent>
                </Card>

                {/* Performance Funnel - Visual Funnel */}
                <Card>
                    <CardHeader>
                        <CardTitle>🔄 Performance Funnel</CardTitle>
                        <CardDescription>Conversion flow from impressions to leads.</CardDescription>
                    </CardHeader>
                    <CardContent className="h-[400px]">
                        {data.platform && data.platform.length > 0 ? (
                            <div className="flex flex-col items-center justify-center h-full space-y-4">
                                {(() => {
                                    // Calculate totals across all platforms
                                    const totals = data.platform.reduce((acc: any, p: any) => ({
                                        impressions: acc.impressions + (p.impressions || 0),
                                        clicks: acc.clicks + (p.clicks || 0),
                                        conversions: acc.conversions + (p.conversions || 0)
                                    }), { impressions: 0, clicks: 0, conversions: 0 });

                                    const ctr = totals.impressions > 0 ? (totals.clicks / totals.impressions * 100).toFixed(1) : '0';
                                    const conversionRate = totals.clicks > 0 ? (totals.conversions / totals.clicks * 100).toFixed(1) : '0';

                                    const formatNumber = (num: number) => {
                                        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
                                        if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
                                        return num.toString();
                                    };

                                    return (
                                        <>
                                            {/* Impressions */}
                                            <div className="relative w-full max-w-md">
                                                <div className="bg-gradient-to-r from-indigo-500 to-indigo-600 text-white rounded-lg p-6 shadow-lg" style={{ clipPath: 'polygon(10% 0%, 90% 0%, 85% 100%, 15% 100%)' }}>
                                                    <div className="text-3xl font-bold text-center">{formatNumber(totals.impressions)}</div>
                                                </div>
                                                <div className="absolute right-0 top-1/2 transform translate-x-full -translate-y-1/2 ml-4 text-sm font-medium whitespace-nowrap">
                                                    → Impressions
                                                </div>
                                            </div>

                                            {/* CTR */}
                                            <div className="text-sm font-semibold text-muted-foreground">
                                                {ctr}% CTR
                                            </div>

                                            {/* Clicks */}
                                            <div className="relative w-full max-w-md" style={{ width: '85%' }}>
                                                <div className="bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-lg p-6 shadow-lg" style={{ clipPath: 'polygon(12% 0%, 88% 0%, 82% 100%, 18% 100%)' }}>
                                                    <div className="text-3xl font-bold text-center">{formatNumber(totals.clicks)}</div>
                                                </div>
                                                <div className="absolute right-0 top-1/2 transform translate-x-full -translate-y-1/2 ml-4 text-sm font-medium whitespace-nowrap">
                                                    → Clicks
                                                </div>
                                            </div>

                                            {/* Conversion Rate */}
                                            <div className="text-sm font-semibold text-muted-foreground">
                                                {conversionRate}% Conversion
                                            </div>

                                            {/* Conversions/Leads */}
                                            <div className="relative w-full max-w-md" style={{ width: '70%' }}>
                                                <div className="bg-gradient-to-r from-cyan-500 to-cyan-600 text-white rounded-lg p-6 shadow-lg" style={{ clipPath: 'polygon(15% 0%, 85% 0%, 78% 100%, 22% 100%)' }}>
                                                    <div className="text-3xl font-bold text-center">{formatNumber(totals.conversions)}</div>
                                                </div>
                                                <div className="absolute right-0 top-1/2 transform translate-x-full -translate-y-1/2 ml-4 text-sm font-medium whitespace-nowrap">
                                                    → Leads
                                                </div>
                                            </div>
                                        </>
                                    );
                                })()}
                            </div>
                        ) : (
                            <div className="flex items-center justify-center h-full text-muted-foreground">
                                No funnel data available
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
