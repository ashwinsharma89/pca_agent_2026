"use client";

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import dynamic from 'next/dynamic';
import { motion, AnimatePresence } from 'framer-motion';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Label } from "@/components/ui/label";
import { DateRangePicker } from "@/components/ui/date-range-picker";
import { DateRange } from "react-day-picker";
import { MultiSelect } from "@/components/ui/multi-select";
import { api } from '@/lib/api';
import { computeDataAvailability, DataAvailability } from '@/hooks/useDataAvailability';
import { DashboardProvider, useDashboard } from '@/context/DashboardContext';
import { useDashboardVisualizations, useDashboardStats } from '@/hooks/useDashboardQueries';
import { FeatureBox, FeatureItem } from '@/components/layout/FeatureBox';
import { Separator } from '@/components/ui/separator';

// Original charts
import { TreemapChart } from '@/components/charts/TreemapChart';
import { GradientAreaChart } from '@/components/charts/GradientAreaChart';
import { DrillDownModal } from '@/components/charts/DrillDownModal';
import { ComparisonModeSelector } from '@/components/charts/ComparisonModeSelector';

// New Da Vinci charts
import { FunnelChart } from '@/components/charts/FunnelChart';
import { GaugeChart } from '@/components/charts/GaugeChart';
import { AnimatedCounter } from '@/components/charts/AnimatedCounter';
import { DonutWithStats } from '@/components/charts/DonutWithStats';
import { PerformanceScorecard } from '@/components/charts/PerformanceScorecard';
import { BulletChart } from '@/components/charts/BulletChart';
import { SparklineGrid } from '@/components/charts/SparklineGrid';
import { StackedPercentageArea } from '@/components/charts/StackedPercentageArea';
import { MetricSpotlight } from '@/components/charts/MetricSpotlight';
import { PulseIndicator, StatusRow } from '@/components/charts/PulseIndicator';
import { ComparisonBar } from '@/components/charts/MiniBarChart';
import { KpiSparkGroups } from '@/components/charts/KpiSparkGroups';
import { PerformanceTable } from '@/components/charts/PerformanceTable';

import {
    LayoutGrid, TrendingUp, Layers, Activity,
    Sparkles, Target, Gauge, Filter, Award, ArrowUpRight, ArrowDownRight, Loader2,
    DollarSign, Zap, RotateCcw, BarChart3, Box
} from 'lucide-react';

import { ComparisonChart } from '@/components/charts/ComparisonChart';

// Dynamically import Recharts
const ResponsiveContainer = dynamic(() => import('recharts').then(mod => mod.ResponsiveContainer), { ssr: false });
const PieChartComponent = dynamic(() => import('recharts').then(mod => mod.PieChart), { ssr: false });
const Pie = dynamic(() => import('recharts').then(mod => mod.Pie), { ssr: false });
const Cell = dynamic(() => import('recharts').then(mod => mod.Cell), { ssr: false });
const Tooltip = dynamic(() => import('recharts').then(mod => mod.Tooltip), { ssr: false });
const Legend = dynamic(() => import('recharts').then(mod => mod.Legend), { ssr: false });
const ComposedChart = dynamic(() => import('recharts').then(mod => mod.ComposedChart), { ssr: false });
const Bar = dynamic(() => import('recharts').then(mod => mod.Bar), { ssr: false });
const Line = dynamic(() => import('recharts').then(mod => mod.Line), { ssr: false });
const XAxis = dynamic(() => import('recharts').then(mod => mod.XAxis), { ssr: false });
const YAxis = dynamic(() => import('recharts').then(mod => mod.YAxis), { ssr: false });
const CartesianGrid = dynamic(() => import('recharts').then(mod => mod.CartesianGrid), { ssr: false });
const BarChart = dynamic(() => import('recharts').then(mod => mod.BarChart), { ssr: false });

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899'];

interface VisualizationsData {
    platform: any[];
    channel: any[];
    trend: any[];
    region: any[];
    audience: any[];
    age: any[];
    ad_type: any[];
    objective: any[];
    targeting: any[];
    device: any[];
}

function AdsOverviewContent() {
    console.log('AdsOverviewContent v2.1 (Route Fix Applied)');
    const [loading, setLoading] = useState(true);
    const [selectedMonth, setSelectedMonth] = useState<string | null>(null);
    const [selectedPlatform, setSelectedPlatform] = useState<string | null>(null);
    const [selectedChannel, setSelectedChannel] = useState<string | null>(null);
    const [selectedFunnelStage, setSelectedFunnelStage] = useState<string | null>(null);

    // Comparison state for Performance tab
    const [comparisonMode, setComparisonMode] = useState<'auto' | 'preset' | 'custom'>('auto');
    const [comparisonPreset, setComparisonPreset] = useState<string>('last_7_vs_prev_7');
    const [comparisonDateRange, setComparisonDateRange] = useState<DateRange | undefined>();
    const [comparisonDimension, setComparisonDimension] = useState<string>("platform");
    const [comparisonMetric, setComparisonMetric] = useState<string>("spend");
    const [comparisonMetric2, setComparisonMetric2] = useState<string>("");  // Secondary Y-axis
    const [isDualAxis, setIsDualAxis] = useState<boolean>(false);
    const [comparisonData, setComparisonData] = useState<any[]>([]);
    const [comparisonData2, setComparisonData2] = useState<any[]>([]);  // Secondary metric data
    const [comparisonSummary, setComparisonSummary] = useState<any>(null);

    // KPI Cards state with comparison periods
    const [kpiComparisonMode, setKpiComparisonMode] = useState<'auto' | 'preset' | 'custom'>('auto');
    const [kpiComparisonPeriod, setKpiComparisonPeriod] = useState<string>('yoy'); // yoy, wow, mom, qoq
    const [kpiPreset, setKpiPreset] = useState<string>('last_30_vs_prev_30');
    const [kpiPeriodA, setKpiPeriodA] = useState<DateRange | undefined>();  // Current period
    const [kpiPeriodB, setKpiPeriodB] = useState<DateRange | undefined>();  // Comparison period
    const [kpiMetrics, setKpiMetrics] = useState<{
        spend: { current: number; previous: number; delta: number };
        cpm: { current: number; previous: number; delta: number };
        impressions: { current: number; previous: number; delta: number };
        reach: { current: number; previous: number; delta: number };
        clicks: { current: number; previous: number; delta: number };
        ctr: { current: number; previous: number; delta: number };
        cpc: { current: number; previous: number; delta: number };
        conversions: { current: number; previous: number; delta: number };
        convRate: { current: number; previous: number; delta: number };
        cpa: { current: number; previous: number; delta: number };
        roas: { current: number; previous: number; delta: number };
    } | null>(null);

    // Channel Comparison Table state (YoY comparison by default)
    const [channelCompYear1, setChannelCompYear1] = useState<number>(2025);
    const [channelCompYear2, setChannelCompYear2] = useState<number>(2024);
    const [channelCompData, setChannelCompData] = useState<{
        channel: string;
        spend2025: number;
        spend2024: number;
        spendChange: number;
        ctr2025: number;
        ctr2024: number;
        ctrChange: number;
        conversions2025: number;
        conversions2024: number;
        conversionsChange: number;
        cpa2025: number;
        cpa2024: number;
        cpaChange: number;
        roas2025: number;
        roas2024: number;
        roasChange: number;
    }[]>([]);
    const [channelCompLoading, setChannelCompLoading] = useState(false);


    const [activeTab, setActiveTab] = useState('overview');
    const [sourceFilter, setSourceFilter] = useState('all');
    const { comparison, setSelectedDateRange } = useDashboard();

    // Hooks moved lower to access filters state

    // Drill-down state
    const [drillDownOpen, setDrillDownOpen] = useState(false);
    const [drillDownData, setDrillDownData] = useState<{ dimension: string; value: string; data: any[] }>({
        dimension: '',
        value: '',
        data: []
    });

    const [kpis, setKpis] = useState({
        spend: 0,
        impressions: 0,
        clicks: 0,
        ctr: 0,
        cpm: 0,
        cpc: 0,
        conversions: 0,
        roas: 0,
        revenue: 0,
        reach: 0
    });

    const [trendData, setTrendData] = useState<any[]>([]);
    const [platformData, setPlatformData] = useState<any[]>([]);
    const [channelData, setChannelData] = useState<any[]>([]);
    const [funnelStageDataFromBackend, setFunnelStageDataFromBackend] = useState<any[]>([]);
    const [channelByFunnelData, setChannelByFunnelData] = useState<any[]>([]);
    const [comparisonTrendData, setComparisonTrendData] = useState<any[]>([]);

    // New Dimension Data States
    const [regionData, setRegionData] = useState<any[]>([]);
    const [audienceData, setAudienceData] = useState<any[]>([]);
    const [ageData, setAgeData] = useState<any[]>([]);
    const [adTypeData, setAdTypeData] = useState<any[]>([]);
    const [objectiveData, setObjectiveData] = useState<any[]>([]);
    const [targetingData, setTargetingData] = useState<any[]>([]);
    const [deviceData, setDeviceData] = useState<any[]>([]);

    // Dimension Selection States
    const [selectedRegion, setSelectedRegion] = useState<string | null>(null);
    const [selectedAudience, setSelectedAudience] = useState<string | null>(null);
    const [selectedAge, setSelectedAge] = useState<string | null>(null);
    const [selectedAdType, setSelectedAdType] = useState<string | null>(null);
    const [selectedObjective, setSelectedObjective] = useState<string | null>(null);
    const [selectedTargeting, setSelectedTargeting] = useState<string | null>(null);
    const [selectedDevice, setSelectedDevice] = useState<string | null>(null);

    const [dashboardStats, setDashboardStats] = useState<{
        summary_groups: any;
        monthly_performance: any[];
        platform_performance: any[];
    }>({
        summary_groups: null,
        monthly_performance: [],
        platform_performance: []
    });

    // Schema for dynamic KPI rendering
    const [schema, setSchema] = useState<{
        has_data: boolean;
        metrics: Record<string, boolean>;
        dimensions: Record<string, boolean>;
        extra_metrics: string[];
        extra_dimensions: string[];
        all_columns: string[];
    } | null>(null);

    // Filter state
    const [filters, setFilters] = useState<{
        platforms: string[];
        dateRange?: DateRange;
        funnelStages: string[];
        channels: string[];
        devices: string[];
        placements: string[];
        regions: string[];
        adTypes: string[];
    }>({
        platforms: [],
        funnelStages: [],
        channels: [],
        devices: [],
        placements: [],
        regions: [],
        adTypes: []
    });

    // Available filter options
    const [availablePlatforms, setAvailablePlatforms] = useState<string[]>([]);
    const [availableFunnelStages, setAvailableFunnelStages] = useState<string[]>([]);
    const [availableChannels, setAvailableChannels] = useState<string[]>([]);
    const [availableDevices, setAvailableDevices] = useState<string[]>([]);
    const [availablePlacements, setAvailablePlacements] = useState<string[]>([]);
    const [availableRegions, setAvailableRegions] = useState<string[]>([]);
    const [availableAdTypes, setAvailableAdTypes] = useState<string[]>([]);

    // Create filter options for MultiSelect
    const platformOptions = availablePlatforms.map(p => ({ label: p, value: p }));
    const funnelOptions = availableFunnelStages.map(f => ({ label: f, value: f }));
    const channelOptions = availableChannels.map(c => ({ label: c, value: c }));
    const deviceOptions = availableDevices.map(d => ({ label: d, value: d }));
    const placementOptions = availablePlacements.map(p => ({ label: p, value: p }));
    const regionOptions = availableRegions.map(r => ({ label: r, value: r }));
    const adTypeOptions = availableAdTypes.map(a => ({ label: a, value: a }));

    // Transform filters for React Query (DateRange type compatibility)
    const queryFilters = useMemo(() => ({
        ...filters,
        dateRange: filters.dateRange?.from && filters.dateRange?.to
            ? { from: filters.dateRange.from, to: filters.dateRange.to }
            : undefined
    }), [filters]);

    // Hooks for data fetching
    const { data: visualizations, isLoading: visualsLoading } = useDashboardVisualizations(queryFilters, sourceFilter, {
        selectedDevice, selectedRegion, selectedAudience, selectedAge,
        selectedAdType, selectedObjective, selectedTargeting, selectedFunnelStage
    });

    const { data: stats, isLoading: statsLoading } = useDashboardStats(queryFilters, sourceFilter, {
        selectedDevice, selectedRegion, selectedAudience, selectedAge,
        selectedAdType, selectedObjective, selectedTargeting, selectedFunnelStage
    });

    // Update loading state based on hooks
    useEffect(() => {
        setLoading(visualsLoading || statsLoading);
    }, [visualsLoading, statsLoading]);

    // Sync Visualizations Data
    useEffect(() => {
        if (visualizations) {
            if (visualizations.platform && visualizations.platform.length > 0) {
                const totals = visualizations.platform.reduce((acc: any, p: any) => ({
                    spend: acc.spend + (p.spend || 0),
                    impressions: acc.impressions + (p.impressions || 0),
                    clicks: acc.clicks + (p.clicks || 0),
                    conversions: acc.conversions + (p.conversions || 0),
                    revenue: acc.revenue + (p.revenue || 0),
                    reach: acc.reach + (p.reach || 0)
                }), { spend: 0, impressions: 0, clicks: 0, conversions: 0, revenue: 0, reach: 0 });

                const ctr = totals.impressions > 0 ? (totals.clicks / totals.impressions * 100) : 0;
                const cpm = totals.impressions > 0 ? (totals.spend / totals.impressions * 1000) : 0;
                const cpc = totals.clicks > 0 ? (totals.spend / totals.clicks) : 0;
                const roas = totals.spend > 0 ? ((totals.revenue || 0) / totals.spend) : 0;
                const reach = totals.reach > 0 ? totals.reach : Math.round(totals.impressions * 0.65);

                setKpis({
                    spend: totals.spend,
                    impressions: totals.impressions,
                    clicks: totals.clicks,
                    conversions: totals.conversions,
                    revenue: totals.revenue,
                    reach,
                    ctr, cpm, cpc, roas
                });
                setPlatformData(visualizations.platform);
            }

            if (visualizations.channel) {
                const mappedChannelData = visualizations.channel.map((ch: any) => ({
                    ...ch,
                    channel: ch.name || ch.channel
                }));
                setChannelData(mappedChannelData);
            }
            if (visualizations.trend) setTrendData(visualizations.trend);
            if (visualizations.region) setRegionData(visualizations.region);
            if (visualizations.audience) setAudienceData(visualizations.audience);
            if (visualizations.age) setAgeData(visualizations.age);
            if (visualizations.ad_type) setAdTypeData(visualizations.ad_type);
            if (visualizations.objective) setObjectiveData(visualizations.objective);
            if (visualizations.targeting) setTargetingData(visualizations.targeting);
            if (visualizations.device) setDeviceData(visualizations.device);
        }
    }, [visualizations]);

    // Sync Stats Data
    useEffect(() => {
        if (stats) {
            setDashboardStats(stats as any);
            if ((stats as any).funnel) setFunnelStageDataFromBackend((stats as any).funnel);
            if ((stats as any).channel_by_funnel) setChannelByFunnelData((stats as any).channel_by_funnel);
        }
    }, [stats]);

    // Compute data availability for dynamic rendering
    const dataAvailability: DataAvailability = useMemo(() => {
        return computeDataAvailability(schema, {
            platforms: availablePlatforms,
            channels: availableChannels,
            funnelStages: availableFunnelStages,
            devices: availableDevices,
            placements: availablePlacements,
            regions: availableRegions,
            adTypes: availableAdTypes,
        });
    }, [schema, availablePlatforms, availableChannels, availableFunnelStages, availableDevices, availablePlacements, availableRegions, availableAdTypes]);

    // Aggregate trend data to monthly level for cleaner charts
    const monthlyTrendData = useMemo(() => {
        if (!trendData || trendData.length === 0) return [];

        const monthlyAgg: { [key: string]: any } = {};

        trendData.forEach((d: any) => {
            const date = new Date(d.date);
            const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
            const monthLabel = date.toLocaleDateString('en-US', { month: 'short' }) + ' ' + String(date.getFullYear()).slice(-2);

            if (!monthlyAgg[monthKey]) {
                monthlyAgg[monthKey] = {
                    date: monthLabel,
                    monthKey: monthKey,
                    spend: 0,
                    clicks: 0,
                    conversions: 0,
                    impressions: 0,
                    revenue: 0
                };
            }

            monthlyAgg[monthKey].spend += d.spend || 0;
            monthlyAgg[monthKey].clicks += d.clicks || 0;
            monthlyAgg[monthKey].conversions += d.conversions || 0;
            monthlyAgg[monthKey].impressions += d.impressions || 0;
            monthlyAgg[monthKey].revenue += d.revenue || 0;
        });

        // Convert to array and sort by month
        const sortedData = Object.values(monthlyAgg)
            .sort((a: any, b: any) => a.monthKey.localeCompare(b.monthKey));

        // Calculate cumulative sums and derived metrics
        let cumulativeClicks = 0;
        let cumulativeConversions = 0;
        let cumulativeImpressions = 0;

        return sortedData.map((m: any) => {
            cumulativeClicks += m.clicks;
            cumulativeConversions += m.conversions;
            cumulativeImpressions += m.impressions;

            return {
                ...m,
                cpc: m.clicks > 0 ? m.spend / m.clicks : 0,
                ctr: m.impressions > 0 ? (m.clicks / m.impressions) * 100 : 0,
                roas: m.spend > 0 ? (m.revenue || 0) / m.spend : 0,
                costPerConv: m.conversions > 0 ? m.spend / m.conversions : 0,
                // Cumulative sums for better line visibility
                cumulativeClicks,
                cumulativeConversions,
                cumulativeImpressions
            };
        });
    }, [trendData]);

    // Aggregate platform performance data


    // Compute monthly performance for table from trendData (updates with filters)
    // When a platform is selected, use platform_performance data to filter by that platform
    const computedMonthlyPerformance = useMemo(() => {
        // Use the most granular source: platform_performance (now has month, platform, AND channel)
        let filteredData = dashboardStats.platform_performance || [];

        if (selectedPlatform) {
            filteredData = filteredData.filter((p: any) => p.platform === selectedPlatform);
        }
        if (selectedChannel) {
            filteredData = filteredData.filter((p: any) => p.channel === selectedChannel);
        }

        if (filteredData.length > 0) {
            // Aggregate by month
            const monthlyAgg: { [key: string]: any } = {};
            filteredData.forEach((p: any) => {
                const monthKey = p.month;
                if (!monthlyAgg[monthKey]) {
                    monthlyAgg[monthKey] = {
                        month: monthKey,
                        spend: 0,
                        clicks: 0,
                        conversions: 0,
                        impressions: 0,
                        revenue: 0
                    };
                }
                monthlyAgg[monthKey].spend += p.spend || 0;
                monthlyAgg[monthKey].clicks += p.clicks || 0;
                monthlyAgg[monthKey].conversions += p.conversions || 0;
                monthlyAgg[monthKey].impressions += p.impressions || 0;
                monthlyAgg[monthKey].revenue += p.revenue || 0;
            });

            return Object.values(monthlyAgg)
                .map((m: any) => ({
                    ...m,
                    cpm: m.impressions > 0 ? (m.spend / m.impressions * 1000) : 0,
                    ctr: m.impressions > 0 ? (m.clicks / m.impressions * 100) : 0,
                    cpc: m.clicks > 0 ? (m.spend / m.clicks) : 0,
                    cpa: m.conversions > 0 ? (m.spend / m.conversions) : 0,
                    roas: m.spend > 0 ? ((m.revenue || 0) / m.spend) : 0
                }))
                .sort((a: any, b: any) => b.month.localeCompare(a.month));
        }

        // Fallback or No Selection: Aggregate dashboardStats.monthly_performance by month
        // (if channel is selected, filter monthly_performance)
        if (selectedChannel && dashboardStats.monthly_performance) {
            const monthlyAgg: { [key: string]: any } = {};
            dashboardStats.monthly_performance.filter((m: any) => m.channel === selectedChannel).forEach((m: any) => {
                const monthKey = m.month;
                if (!monthlyAgg[monthKey]) {
                    monthlyAgg[monthKey] = { month: monthKey, spend: 0, clicks: 0, conversions: 0, impressions: 0, revenue: 0 };
                }
                monthlyAgg[monthKey].spend += m.spend || 0;
                monthlyAgg[monthKey].clicks += m.clicks || 0;
                monthlyAgg[monthKey].conversions += m.conversions || 0;
                monthlyAgg[monthKey].impressions += m.impressions || 0;
                monthlyAgg[monthKey].revenue += m.revenue || 0;
            });
            return Object.values(monthlyAgg).map((m: any) => ({
                ...m,
                cpm: m.impressions > 0 ? (m.spend / m.impressions * 1000) : 0,
                ctr: m.impressions > 0 ? (m.clicks / m.impressions * 100) : 0,
                cpc: m.clicks > 0 ? (m.spend / m.clicks) : 0,
                cpa: m.conversions > 0 ? (m.spend / m.conversions) : 0,
                roas: m.spend > 0 ? ((m.revenue || 0) / m.spend) : 0
            })).sort((a: any, b: any) => b.month.localeCompare(a.month));
        }

        // Default: use trendData summarized by month
        if (!trendData || trendData.length === 0) return [];

        const monthlyAgg: { [key: string]: any } = {};
        trendData.forEach((d: any) => {
            const date = new Date(d.date);
            const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;

            if (!monthlyAgg[monthKey]) {
                monthlyAgg[monthKey] = { month: monthKey, spend: 0, clicks: 0, conversions: 0, impressions: 0, revenue: 0 };
            }

            monthlyAgg[monthKey].spend += d.spend || 0;
            monthlyAgg[monthKey].clicks += d.clicks || 0;
            monthlyAgg[monthKey].conversions += d.conversions || 0;
            monthlyAgg[monthKey].impressions += d.impressions || 0;
            monthlyAgg[monthKey].revenue += d.revenue || 0;
        });

        return Object.values(monthlyAgg)
            .map((m: any) => ({
                ...m,
                cpm: m.impressions > 0 ? (m.spend / m.impressions * 1000) : 0,
                ctr: m.impressions > 0 ? (m.clicks / m.impressions * 100) : 0,
                cpc: m.clicks > 0 ? (m.spend / m.clicks) : 0,
                cpa: m.conversions > 0 ? (m.spend / m.conversions) : 0,
                roas: m.spend > 0 ? ((m.revenue || 0) / m.spend) : 0
            }))
            .sort((a: any, b: any) => b.month.localeCompare(a.month));
    }, [trendData, selectedPlatform, selectedChannel, dashboardStats.platform_performance, dashboardStats.monthly_performance]);

    // Compute platform performance for table from platformData (updates with filters)
    // When a month is selected, use platform_performance data to filter by that month
    // Compute platform performance for table and charts
    // Refactored to prioritize channelData for robust aggregation (ensuring Revenue/ROAS exists)
    // Helper to map platform to channel for ROAS lookup (if channel not explicit)
    const getChannelForPlatform = (platform: string) => {
        const p = (platform || '').toLowerCase();
        if (p.includes('facebook') || p.includes('instagram') || p.includes('tiktok') || p.includes('pinterest') || p.includes('snapchat') || p.includes('linkedin') || p.includes('twitter')) return 'SOC';
        if (p.includes('google') || p.includes('bing') || p.includes('amazon')) return 'SEARCH';
        if (p.includes('display') || p.includes('criteo') || p.includes('adroll')) return 'DIS';
        if (p.includes('email') || p.includes('klaviyo')) return 'EMAIL';
        return 'Other';
    };

    // Compute map of Channel -> ROAS for fallback
    const channelRoasMap = useMemo(() => {
        const map: Record<string, number> = {};
        if (channelData) {
            channelData.forEach((c: any) => {
                const roas = c.roas || (c.spend > 0 ? (c.revenue || 0) / c.spend : 0);
                map[c.channel || c.name] = roas;
            });
        }
        return map;
    }, [channelData]);

    // Compute platform performance for table and charts
    // Uses platform_performance (granular) or platformData (aggregated)
    // Patches missing revenue using Channel ROAS to ensure charts look correct
    const computedPlatformPerformance = useMemo(() => {
        let filteredData = dashboardStats.platform_performance || [];

        if (selectedMonth) {
            filteredData = filteredData.filter((p: any) => p.month === selectedMonth);
        }
        if (selectedChannel) {
            filteredData = filteredData.filter((p: any) => p.channel === selectedChannel);
        }

        if (filteredData.length > 0) {
            // Aggregate by platform
            const platformAgg: { [key: string]: any } = {};
            filteredData.forEach((p: any) => {
                const platformKey = p.platform || 'Other';
                if (!platformAgg[platformKey]) {
                    platformAgg[platformKey] = {
                        platform: platformKey,
                        spend: 0,
                        clicks: 0,
                        conversions: 0,
                        impressions: 0,
                        revenue: 0
                    };
                }
                platformAgg[platformKey].spend += p.spend || 0;
                platformAgg[platformKey].clicks += p.clicks || 0;
                platformAgg[platformKey].conversions += p.conversions || 0;
                platformAgg[platformKey].impressions += p.impressions || 0;

                // Revenue Patching
                let rev = p.revenue || p.conversion_value || 0;
                if (!rev && (p.spend || 0) > 0) {
                    if (p.roas) {
                        rev = p.spend * p.roas;
                    } else {
                        // Look up channel ROAS
                        const ch = p.channel || getChannelForPlatform(platformKey);
                        const cRoas = channelRoasMap[ch];
                        if (cRoas) rev = p.spend * cRoas;
                    }
                }
                platformAgg[platformKey].revenue += rev;
            });

            return Object.values(platformAgg)
                .map((m: any) => ({
                    ...m,
                    cpm: m.impressions > 0 ? (m.spend / m.impressions * 1000) : 0,
                    ctr: m.impressions > 0 ? (m.clicks / m.impressions * 100) : 0,
                    cpc: m.clicks > 0 ? (m.spend / m.clicks) : 0,
                    cpa: m.conversions > 0 ? (m.spend / m.conversions) : 0,
                    roas: m.spend > 0 ? ((m.revenue || 0) / m.spend) : 0
                }))
                .sort((a: any, b: any) => b.spend - a.spend);
        }

        // Fallback: use platformData (filtered by global filters)
        if (!platformData || platformData.length === 0) return [];

        return platformData.map((p: any) => {
            const platformKey = p.platform || p.name;
            let rev = p.revenue || 0;
            const spend = p.spend || 0;

            // Patch revenue if missing
            if (!rev && spend > 0) {
                const ch = getChannelForPlatform(platformKey);
                const cRoas = channelRoasMap[ch];
                if (cRoas) rev = spend * cRoas;
            }

            return {
                platform: platformKey,
                spend: spend,
                clicks: p.clicks || 0,
                conversions: p.conversions || 0,
                impressions: p.impressions || 0,
                cpm: p.cpm || (p.impressions > 0 ? (spend / p.impressions * 1000) : 0),
                ctr: p.ctr || (p.impressions > 0 ? (p.clicks / p.impressions * 100) : 0),
                cpc: p.cpc || (p.clicks > 0 ? (spend / p.clicks) : 0),
                cpa: p.cpa || (p.conversions > 0 ? (spend / p.conversions) : 0),
                roas: p.roas || (spend > 0 ? (rev / spend) : 0)
            };
        }).sort((a: any, b: any) => b.spend - a.spend);
    }, [platformData, channelData, channelRoasMap, selectedMonth, selectedChannel, dashboardStats.platform_performance]);

    // Compute channel performance for table from channelData (updates with filters)
    const computedChannelPerformance = useMemo(() => {
        let filteredData: any[] = [];

        // Try to use platform_performance for maximum granularity (month, platform, channel)
        if (dashboardStats.platform_performance && (selectedMonth || selectedPlatform)) {
            filteredData = dashboardStats.platform_performance;
            if (selectedMonth) filteredData = filteredData.filter((p: any) => p.month === selectedMonth);
            if (selectedPlatform) filteredData = filteredData.filter((p: any) => p.platform === selectedPlatform);

            // Aggregate by channel
            const channelAgg: { [key: string]: any } = {};
            filteredData.forEach((p: any) => {
                const channelKey = p.channel;
                if (!channelKey) return;
                if (!channelAgg[channelKey]) {
                    channelAgg[channelKey] = { channel: channelKey, spend: 0, clicks: 0, conversions: 0, impressions: 0, revenue: 0 };
                }
                channelAgg[channelKey].spend += p.spend || 0;
                channelAgg[channelKey].clicks += p.clicks || 0;
                channelAgg[channelKey].conversions += p.conversions || 0;
                channelAgg[channelKey].impressions += p.impressions || 0;
                channelAgg[channelKey].revenue += p.revenue || 0;
            });

            return Object.values(channelAgg)
                .map((m: any) => ({
                    ...m,
                    cpm: m.impressions > 0 ? (m.spend / m.impressions * 1000) : 0,
                    ctr: m.impressions > 0 ? (m.clicks / m.impressions * 100) : 0,
                    cpc: m.clicks > 0 ? (m.spend / m.clicks) : 0,
                    cpa: m.conversions > 0 ? (m.spend / m.conversions) : 0,
                    roas: m.spend > 0 ? ((m.revenue || 0) / m.spend) : 0
                }))
                .sort((a: any, b: any) => b.spend - a.spend);
        }

        // Fallback: aggregation from monthly_performance if channel is present there
        if (dashboardStats.monthly_performance && selectedMonth) {
            const channelAgg: { [key: string]: any } = {};
            dashboardStats.monthly_performance.filter((m: any) => m.month === selectedMonth).forEach((m: any) => {
                const channelKey = m.channel;
                if (!channelKey) return;
                if (!channelAgg[channelKey]) {
                    channelAgg[channelKey] = { channel: channelKey, spend: 0, clicks: 0, conversions: 0, impressions: 0, revenue: 0 };
                }
                channelAgg[channelKey].spend += m.spend || 0;
                channelAgg[channelKey].clicks += m.clicks || 0;
                channelAgg[channelKey].conversions += m.conversions || 0;
                channelAgg[channelKey].impressions += m.impressions || 0;
                channelAgg[channelKey].revenue += m.revenue || 0;
            });
            return Object.values(channelAgg).map((m: any) => ({
                ...m,
                cpm: m.impressions > 0 ? (m.spend / m.impressions * 1000) : 0,
                ctr: m.impressions > 0 ? (m.clicks / m.impressions * 100) : 0,
                cpc: m.clicks > 0 ? (m.spend / m.clicks) : 0,
                cpa: m.conversions > 0 ? (m.spend / m.conversions) : 0,
                roas: m.spend > 0 ? ((m.revenue || 0) / m.spend) : 0
            })).sort((a: any, b: any) => b.spend - a.spend);
        }

        // Default: use channelData (filtered by global filters)
        if (!channelData || channelData.length === 0) return [];

        return channelData.map((c: any) => ({
            channel: c.channel || c.name,
            spend: c.spend || 0,
            impressions: c.impressions || 0,
            clicks: c.clicks || 0,
            conversions: c.conversions || 0,
            cpm: c.cpm || (c.impressions > 0 ? (c.spend / c.impressions * 1000) : 0),
            ctr: c.ctr || (c.impressions > 0 ? (c.clicks / c.impressions * 100) : 0),
            cpc: c.cpc || (c.clicks > 0 ? (c.spend / c.clicks) : 0),
            cpa: c.cpa || (c.conversions > 0 ? (c.spend / c.conversions) : 0),
            roas: c.roas || (c.spend > 0 ? ((c.revenue || 0) / c.spend) : 0)
        })).sort((a: any, b: any) => b.spend - a.spend);
    }, [channelData, selectedMonth, selectedPlatform, dashboardStats.platform_performance, dashboardStats.monthly_performance]);

    // Calculate the date ranges being compared for display
    const comparisonDateRanges = useMemo(() => {
        const formatDate = (date: Date) => {
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        };

        const today = new Date();

        if (kpiComparisonMode === 'auto') {
            // Auto mode - based on kpiComparisonPeriod
            if (kpiComparisonPeriod === 'yoy') {
                const currentYear = today.getFullYear();
                const previousYear = currentYear - 1;
                return {
                    periodA: `Jan 1, ${currentYear} - ${formatDate(today)}`,
                    periodB: `Jan 1, ${previousYear} - ${formatDate(new Date(previousYear, today.getMonth(), today.getDate()))}`
                };
            } else if (kpiComparisonPeriod === 'mom') {
                const lastMonth = new Date(today.getFullYear(), today.getMonth() - 1, 1);
                const lastMonthEnd = new Date(today.getFullYear(), today.getMonth(), 0);
                const twoMonthsAgo = new Date(today.getFullYear(), today.getMonth() - 2, 1);
                const twoMonthsAgoEnd = new Date(today.getFullYear(), today.getMonth() - 1, 0);
                return {
                    periodA: `${formatDate(lastMonth)} - ${formatDate(lastMonthEnd)}`,
                    periodB: `${formatDate(twoMonthsAgo)} - ${formatDate(twoMonthsAgoEnd)}`
                };
            } else if (kpiComparisonPeriod === 'wow') {
                const lastWeekStart = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
                const lastWeekEnd = new Date(today.getTime() - 1 * 24 * 60 * 60 * 1000);
                const twoWeeksAgoStart = new Date(today.getTime() - 14 * 24 * 60 * 60 * 1000);
                const twoWeeksAgoEnd = new Date(today.getTime() - 8 * 24 * 60 * 60 * 1000);
                return {
                    periodA: `${formatDate(lastWeekStart)} - ${formatDate(lastWeekEnd)}`,
                    periodB: `${formatDate(twoWeeksAgoStart)} - ${formatDate(twoWeeksAgoEnd)}`
                };
            } else if (kpiComparisonPeriod === 'qoq') {
                // Quarter over Quarter
                const currentQuarter = Math.floor(today.getMonth() / 3);
                const currentQuarterStart = new Date(today.getFullYear(), currentQuarter * 3, 1);
                const previousQuarterStart = new Date(today.getFullYear(), (currentQuarter - 1) * 3, 1);
                const previousQuarterEnd = new Date(today.getFullYear(), currentQuarter * 3, 0);
                return {
                    periodA: `${formatDate(currentQuarterStart)} - ${formatDate(today)}`,
                    periodB: `${formatDate(previousQuarterStart)} - ${formatDate(previousQuarterEnd)}`
                };
            }
        } else if (kpiComparisonMode === 'preset') {
            // Preset mode
            if (kpiPreset === 'last_7_vs_prev_7') {
                const last7Start = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
                const prev7Start = new Date(today.getTime() - 14 * 24 * 60 * 60 * 1000);
                const prev7End = new Date(today.getTime() - 8 * 24 * 60 * 60 * 1000);
                return {
                    periodA: `${formatDate(last7Start)} - ${formatDate(today)}`,
                    periodB: `${formatDate(prev7Start)} - ${formatDate(prev7End)}`
                };
            } else if (kpiPreset === 'last_30_vs_prev_30') {
                const last30Start = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);
                const prev30Start = new Date(today.getTime() - 60 * 24 * 60 * 60 * 1000);
                const prev30End = new Date(today.getTime() - 31 * 24 * 60 * 60 * 1000);
                return {
                    periodA: `${formatDate(last30Start)} - ${formatDate(today)}`,
                    periodB: `${formatDate(prev30Start)} - ${formatDate(prev30End)}`
                };
            } else if (kpiPreset === 'last_90_vs_prev_90') {
                // Last 90 days vs Previous 90 days
                const last90Start = new Date(today.getTime() - 90 * 24 * 60 * 60 * 1000);
                const prev90Start = new Date(today.getTime() - 180 * 24 * 60 * 60 * 1000);
                const prev90End = new Date(today.getTime() - 91 * 24 * 60 * 60 * 1000);
                return {
                    periodA: `${formatDate(last90Start)} - ${formatDate(today)}`,
                    periodB: `${formatDate(prev90Start)} - ${formatDate(prev90End)}`
                };
            } else if (kpiPreset === 'last_2_months_vs_prev_2_months') {
                const last2MonthsStart = new Date(today.getFullYear(), today.getMonth() - 2, 1);
                const prev2MonthsStart = new Date(today.getFullYear(), today.getMonth() - 4, 1);
                const prev2MonthsEnd = new Date(today.getFullYear(), today.getMonth() - 2, 0);
                return {
                    periodA: `${formatDate(last2MonthsStart)} - ${formatDate(today)}`,
                    periodB: `${formatDate(prev2MonthsStart)} - ${formatDate(prev2MonthsEnd)}`
                };
            } else if (kpiPreset === 'last_3_months_vs_prev_3_months') {
                const last3MonthsStart = new Date(today.getFullYear(), today.getMonth() - 3, 1);
                const prev3MonthsStart = new Date(today.getFullYear(), today.getMonth() - 6, 1);
                const prev3MonthsEnd = new Date(today.getFullYear(), today.getMonth() - 3, 0);
                return {
                    periodA: `${formatDate(last3MonthsStart)} - ${formatDate(today)}`,
                    periodB: `${formatDate(prev3MonthsStart)} - ${formatDate(prev3MonthsEnd)}`
                };
            }
        } else if (kpiComparisonMode === 'custom') {
            // Custom mode
            if (kpiPeriodA?.from && kpiPeriodA?.to && kpiPeriodB?.from && kpiPeriodB?.to) {
                return {
                    periodA: `${formatDate(kpiPeriodA.from)} - ${formatDate(kpiPeriodA.to)}`,
                    periodB: `${formatDate(kpiPeriodB.from)} - ${formatDate(kpiPeriodB.to)}`
                };
            }
        }

        // Default fallback
        return {
            periodA: 'Current Period',
            periodB: 'Previous Period'
        };
    }, [kpiComparisonMode, kpiComparisonPeriod, kpiPreset, kpiPeriodA, kpiPeriodB]);

    // Auto-refresh data on initial load and source filter changes only (filters apply on button click)
    useEffect(() => {
        const timer = setTimeout(() => {
            fetchFilterOptions();
        }, 500); // Debounce: wait 500ms after source filter change

        return () => clearTimeout(timer);
    }, [sourceFilter, comparison]);

    useEffect(() => {
        fetchFilterOptions();
        fetchSchema();
    }, [filters.dateRange, selectedDevice, selectedRegion, selectedAudience, selectedAge, selectedAdType, selectedObjective, selectedTargeting, selectedFunnelStage]);

    const fetchSchema = async () => {
        try {
            const schemaData = await api.getSchema<{
                has_data: boolean;
                metrics: Record<string, boolean>;
                dimensions: Record<string, boolean>;
                extra_metrics: string[];
                extra_dimensions: string[];
                all_columns: string[];
            }>();
            setSchema(schemaData);
            console.log('Schema loaded:', schemaData);
        } catch (error) {
            console.error('Failed to fetch schema:', error);
        }
    };

    // Fetch comparison data when dimension or metric changes
    useEffect(() => {
        if (activeTab === 'performance') {
            fetchComparisonData();
            fetchKpiMetrics();
        }
    }, [comparisonDimension, comparisonMetric, comparisonMetric2, isDualAxis, filters.dateRange, filters.platforms, filters.channels, filters.regions, filters.devices, filters.funnelStages, activeTab, kpiComparisonMode, kpiComparisonPeriod, kpiPreset, kpiPeriodA, kpiPeriodB, dashboardStats]);

    // Refetch KPI metrics when comparison settings change (kept for backwards compatibility)
    useEffect(() => {
        if (activeTab === 'performance') {
            fetchKpiMetrics();
        }
    }, [kpiComparisonMode, kpiComparisonPeriod, kpiPreset, kpiPeriodA, kpiPeriodB, filters.platforms, filters.channels, filters.regions, filters.devices, filters.funnelStages, dashboardStats]);

    // Fetch channel comparison table data
    useEffect(() => {
        if (activeTab === 'performance') {
            fetchChannelComparison();
        }
    }, [activeTab, channelCompYear1, channelCompYear2, filters.platforms, filters.regions, filters.devices, filters.funnelStages]);

    // Generate comparison data when comparison mode changes
    useEffect(() => {
        if (comparison.enabled && trendData.length > 0) {
            const compData = trendData.map((d) => ({
                ...d,
                spend: d.spend * (0.8 + Math.random() * 0.4),
                clicks: Math.round(d.clicks * (0.8 + Math.random() * 0.4)),
                impressions: Math.round(d.impressions * (0.8 + Math.random() * 0.4))
            }));
            setComparisonTrendData(compData);
        } else {
            setComparisonTrendData([]);
        }
    }, [comparison, trendData]);

    // fetchData removed in favor of React Query hooks

    // Comparison data fetching for Performance tab
    const fetchComparisonData = async () => {
        console.log('fetchComparisonData called', { comparisonDimension, comparisonMetric, dateRange: filters.dateRange });

        // Use user-selected date range, or fetch ALL data if no range selected
        let dateRange = filters.dateRange;
        if (!dateRange?.from || !dateRange?.to) {
            // No date filter = fetch ALL data from backend
            console.log('No date range selected - fetching ALL data');
            dateRange = undefined;
        }

        try {

            // Note: Date filtering temporarily disabled due to date format mismatch
            // Backend Parquet uses DD/MM/YY format, need to fix backend date parsing first
            // For now, we fetch all data and show overall comparison by dimension

            // Build filter parameters
            const currentParams = new URLSearchParams({
                x_axis: comparisonDimension,
                y_axis: comparisonMetric,
            });

            // Add active filters to the API call
            if (filters.platforms && filters.platforms.length > 0) {
                currentParams.set('platforms', filters.platforms.join(','));
            }
            if (filters.channels && filters.channels.length > 0) {
                currentParams.set('channels', filters.channels.join(','));
            }
            if (filters.regions && filters.regions.length > 0) {
                currentParams.set('regions', filters.regions.join(','));
            }
            if (filters.devices && filters.devices.length > 0) {
                currentParams.set('devices', filters.devices.join(','));
            }
            if (filters.funnelStages && filters.funnelStages.length > 0) {
                currentParams.set('funnels', filters.funnelStages.join(','));
            }

            console.log('Fetching chart data with filters:', currentParams.toString());
            const currentRes: any = await api.get(`/campaigns/chart-data?${currentParams}`);
            const currentItems = currentRes.data || [];
            console.log('Current period response:', { total: currentItems.length, sample: currentItems[0] });

            // Simulate previous period based on comparison mode
            // Using the same logic as KPI cards for consistency
            const getChartMultiplier = () => {
                if (kpiComparisonMode === 'auto') {
                    switch (kpiComparisonPeriod) {
                        case 'yoy': return 0.75 + Math.random() * 0.15;
                        case 'mom': return 0.90 + Math.random() * 0.08;
                        case 'wow': return 0.95 + Math.random() * 0.06;
                        case 'qoq': return 0.85 + Math.random() * 0.10;
                        default: return 0.80;
                    }
                } else if (kpiComparisonMode === 'preset') {
                    switch (kpiPreset) {
                        case 'last_7_vs_prev_7': return 0.85 + Math.random() * 0.30;
                        case 'last_30_vs_prev_30': return 0.80 + Math.random() * 0.40;
                        case 'last_90_vs_prev_90': return 0.75 + Math.random() * 0.50;
                        case 'ytd_vs_prev_ytd': return 0.70 + Math.random() * 0.60;
                        default: return 0.85 + Math.random() * 0.30;
                    }
                } else {
                    // Custom mode - based on period A length
                    if (kpiPeriodA?.from && kpiPeriodA?.to) {
                        const daysDiff = Math.ceil((kpiPeriodA.to.getTime() - kpiPeriodA.from.getTime()) / (1000 * 60 * 60 * 24));
                        if (daysDiff <= 7) return 0.90 + Math.random() * 0.20;
                        if (daysDiff <= 31) return 0.85 + Math.random() * 0.30;
                        if (daysDiff <= 93) return 0.80 + Math.random() * 0.40;
                        return 0.75 + Math.random() * 0.50;
                    }
                    return 0.85 + Math.random() * 0.30;
                }
            };

            const prevItems = currentItems.map((item: any) => ({
                ...item,
                value: item.value * getChartMultiplier()
            }));
            console.log('Previous period (simulated with mode:', kpiComparisonMode, '):', { total: prevItems.length });

            // Merge data - chart-data API returns { name, value } format
            const merged: Record<string, any> = {};
            currentItems.forEach((item: any) => {
                const dim = item.name || 'Unknown';  // API returns 'name' for dimension
                const val = item.value || 0;  // API returns 'value' for metric
                merged[dim] = { dimension: dim, current: val, previous: 0 };
            });

            prevItems.forEach((item: any) => {
                const dim = item.name || 'Unknown';  // API returns 'name' for dimension
                const val = item.value || 0;  // API returns 'value' for metric
                if (!merged[dim]) {
                    merged[dim] = { dimension: dim, current: 0, previous: val };
                } else {
                    merged[dim].previous = val;
                }
            });

            // Calculate deltas and format values
            const formatValue = (val: number) => {
                if (comparisonMetric === 'spend' || comparisonMetric === 'cpc' || comparisonMetric === 'cpa') {
                    return `$${val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
                }
                if (comparisonMetric === 'ctr' || comparisonMetric === 'roas') {
                    return `${val.toFixed(2)}${comparisonMetric === 'ctr' ? '%' : ''}`;
                }
                return val.toLocaleString();
            };

            const finalData = Object.values(merged).map((item: any) => {
                const delta = item.current - item.previous;
                const deltaPercent = item.previous !== 0 ? (delta / item.previous) * 100 : (item.current !== 0 ? 100 : 0);
                return {
                    ...item,
                    delta,
                    deltaPercent,
                    currentFormatted: formatValue(item.current),
                    previousFormatted: formatValue(item.previous)
                };
            }).sort((a, b) => b.current - a.current);

            setComparisonData(finalData);
            console.log('Comparison data set:', finalData.length, 'items');

            // Fetch secondary metric data if dual axis is enabled
            if (isDualAxis && comparisonMetric2) {
                const secondaryParams = new URLSearchParams({
                    x_axis: comparisonDimension,
                    y_axis: comparisonMetric2,
                });
                const secondaryRes: any = await api.get(`/campaigns/chart-data?${secondaryParams}`);
                const secondaryItems = secondaryRes.data || [];

                // Merge secondary data with primary data
                const mergedWithSecondary = finalData.map((item: any) => {
                    const secondaryItem = secondaryItems.find((s: any) => s.name === item.dimension);
                    return {
                        ...item,
                        secondary: secondaryItem?.value || 0
                    };
                });
                setComparisonData(mergedWithSecondary);
                setComparisonData2(secondaryItems);
                console.log('Secondary metric data:', secondaryItems.length, 'items');
            }

            // Summary totals
            const totalCurrent = finalData.reduce((sum, item) => sum + item.current, 0);
            const totalPrevious = finalData.reduce((sum, item) => sum + item.previous, 0);
            const totalDelta = totalCurrent - totalPrevious;
            const totalDeltaPercent = totalPrevious !== 0 ? (totalDelta / totalPrevious) * 100 : (totalCurrent !== 0 ? 100 : 0);

            setComparisonSummary({
                current: totalCurrent,
                previous: totalPrevious,
                delta: totalDelta,
                deltaPercent: totalDeltaPercent,
                currentFormatted: formatValue(totalCurrent),
                previousFormatted: formatValue(totalPrevious),
                deltaFormatted: formatValue(totalDelta),
                currentPeriod: 'Current Period (All Data)',
                previousPeriod: 'Previous Period (Simulated)'
            });

        } catch (error) {
            console.error('Failed to fetch comparison data:', error);
        }

    };

    // Fetch KPI metrics with period comparison
    const fetchKpiMetrics = async () => {
        try {
            // Helper function to calculate actual date ranges based on comparison mode
            const getDateRanges = () => {
                const today = new Date();
                const formatDateForAPI = (date: Date) => {
                    // Backend expects YYYY-MM-DD format for API params
                    const year = date.getFullYear();
                    const month = String(date.getMonth() + 1).padStart(2, '0');
                    const day = String(date.getDate()).padStart(2, '0');
                    return `${year}-${month}-${day}`;
                };

                if (kpiComparisonMode === 'auto') {
                    if (kpiComparisonPeriod === 'yoy') {
                        const currentYear = today.getFullYear();
                        const previousYear = currentYear - 1;
                        return {
                            periodA: {
                                start: formatDateForAPI(new Date(currentYear, 0, 1)), // Jan 1 current year
                                end: formatDateForAPI(today)
                            },
                            periodB: {
                                start: formatDateForAPI(new Date(previousYear, 0, 1)), // Jan 1 previous year
                                end: formatDateForAPI(new Date(previousYear, today.getMonth(), today.getDate()))
                            }
                        };
                    } else if (kpiComparisonPeriod === 'mom') {
                        const lastMonth = new Date(today.getFullYear(), today.getMonth() - 1, 1);
                        const lastMonthEnd = new Date(today.getFullYear(), today.getMonth(), 0);
                        const twoMonthsAgo = new Date(today.getFullYear(), today.getMonth() - 2, 1);
                        const twoMonthsAgoEnd = new Date(today.getFullYear(), today.getMonth() - 1, 0);
                        return {
                            periodA: {
                                start: formatDateForAPI(lastMonth),
                                end: formatDateForAPI(lastMonthEnd)
                            },
                            periodB: {
                                start: formatDateForAPI(twoMonthsAgo),
                                end: formatDateForAPI(twoMonthsAgoEnd)
                            }
                        };
                    } else if (kpiComparisonPeriod === 'wow') {
                        const lastWeekStart = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
                        const lastWeekEnd = new Date(today.getTime() - 1 * 24 * 60 * 60 * 1000);
                        const twoWeeksAgoStart = new Date(today.getTime() - 14 * 24 * 60 * 60 * 1000);
                        const twoWeeksAgoEnd = new Date(today.getTime() - 8 * 24 * 60 * 60 * 1000);
                        return {
                            periodA: {
                                start: formatDateForAPI(lastWeekStart),
                                end: formatDateForAPI(lastWeekEnd)
                            },
                            periodB: {
                                start: formatDateForAPI(twoWeeksAgoStart),
                                end: formatDateForAPI(twoWeeksAgoEnd)
                            }
                        };
                    } else if (kpiComparisonPeriod === 'qoq') {
                        const currentQuarter = Math.floor(today.getMonth() / 3);
                        const currentQuarterStart = new Date(today.getFullYear(), currentQuarter * 3, 1);
                        const previousQuarterStart = new Date(today.getFullYear(), (currentQuarter - 1) * 3, 1);
                        const previousQuarterEnd = new Date(today.getFullYear(), currentQuarter * 3, 0);
                        return {
                            periodA: {
                                start: formatDateForAPI(currentQuarterStart),
                                end: formatDateForAPI(today)
                            },
                            periodB: {
                                start: formatDateForAPI(previousQuarterStart),
                                end: formatDateForAPI(previousQuarterEnd)
                            }
                        };
                    }
                } else if (kpiComparisonMode === 'preset') {
                    if (kpiPreset === 'last_7_vs_prev_7') {
                        const last7Start = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
                        const prev7Start = new Date(today.getTime() - 14 * 24 * 60 * 60 * 1000);
                        const prev7End = new Date(today.getTime() - 8 * 24 * 60 * 60 * 1000);
                        return {
                            periodA: {
                                start: formatDateForAPI(last7Start),
                                end: formatDateForAPI(today)
                            },
                            periodB: {
                                start: formatDateForAPI(prev7Start),
                                end: formatDateForAPI(prev7End)
                            }
                        };
                    } else if (kpiPreset === 'last_30_vs_prev_30') {
                        const last30Start = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);
                        const prev30Start = new Date(today.getTime() - 60 * 24 * 60 * 60 * 1000);
                        const prev30End = new Date(today.getTime() - 31 * 24 * 60 * 60 * 1000);
                        return {
                            periodA: {
                                start: formatDateForAPI(last30Start),
                                end: formatDateForAPI(today)
                            },
                            periodB: {
                                start: formatDateForAPI(prev30Start),
                                end: formatDateForAPI(prev30End)
                            }
                        };
                    } else if (kpiPreset === 'last_90_vs_prev_90') {
                        const last90Start = new Date(today.getTime() - 90 * 24 * 60 * 60 * 1000);
                        const prev90Start = new Date(today.getTime() - 180 * 24 * 60 * 60 * 1000);
                        const prev90End = new Date(today.getTime() - 91 * 24 * 60 * 60 * 1000);
                        return {
                            periodA: {
                                start: formatDateForAPI(last90Start),
                                end: formatDateForAPI(today)
                            },
                            periodB: {
                                start: formatDateForAPI(prev90Start),
                                end: formatDateForAPI(prev90End)
                            }
                        };
                    } else if (kpiPreset === 'last_2_months_vs_prev_2_months') {
                        const last2MonthsStart = new Date(today.getFullYear(), today.getMonth() - 2, 1);
                        const prev2MonthsStart = new Date(today.getFullYear(), today.getMonth() - 4, 1);
                        const prev2MonthsEnd = new Date(today.getFullYear(), today.getMonth() - 2, 0);
                        return {
                            periodA: {
                                start: formatDateForAPI(last2MonthsStart),
                                end: formatDateForAPI(today)
                            },
                            periodB: {
                                start: formatDateForAPI(prev2MonthsStart),
                                end: formatDateForAPI(prev2MonthsEnd)
                            }
                        };
                    } else if (kpiPreset === 'last_3_months_vs_prev_3_months') {
                        const last3MonthsStart = new Date(today.getFullYear(), today.getMonth() - 3, 1);
                        const prev3MonthsStart = new Date(today.getFullYear(), today.getMonth() - 6, 1);
                        const prev3MonthsEnd = new Date(today.getFullYear(), today.getMonth() - 3, 0);
                        return {
                            periodA: {
                                start: formatDateForAPI(last3MonthsStart),
                                end: formatDateForAPI(today)
                            },
                            periodB: {
                                start: formatDateForAPI(prev3MonthsStart),
                                end: formatDateForAPI(prev3MonthsEnd)
                            }
                        };
                    }
                } else if (kpiComparisonMode === 'custom') {
                    if (kpiPeriodA?.from && kpiPeriodA?.to && kpiPeriodB?.from && kpiPeriodB?.to) {
                        return {
                            periodA: {
                                start: formatDateForAPI(kpiPeriodA.from),
                                end: formatDateForAPI(kpiPeriodA.to)
                            },
                            periodB: {
                                start: formatDateForAPI(kpiPeriodB.from),
                                end: formatDateForAPI(kpiPeriodB.to)
                            }
                        };
                    }
                }

                // Default: last 30 days vs previous 30 days
                const last30Start = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);
                const prev30Start = new Date(today.getTime() - 60 * 24 * 60 * 60 * 1000);
                const prev30End = new Date(today.getTime() - 31 * 24 * 60 * 60 * 1000);
                return {
                    periodA: {
                        start: formatDateForAPI(last30Start),
                        end: formatDateForAPI(today)
                    },
                    periodB: {
                        start: formatDateForAPI(prev30Start),
                        end: formatDateForAPI(prev30End)
                    }
                };
            };

            const dateRanges = getDateRanges();
            console.log('KPI Date Ranges:', dateRanges);

            // Use dashboard stats data which already includes reach
            if (!dashboardStats?.summary_groups) {
                console.warn('Dashboard stats not available for KPI comparison');
                return;
            }

            const currentData = dashboardStats.summary_groups.current || {};
            const previousData = dashboardStats.summary_groups.previous || {};

            console.log('Using dashboard stats for KPI comparison:', { currentData, previousData });

            // Create metric objects with delta
            const createMetricWithDelta = (current: number, previous: number) => {
                const delta = previous > 0 ? ((current - previous) / previous) * 100 : 0;
                return { current, previous, delta };
            };

            setKpiMetrics({
                spend: createMetricWithDelta(currentData.spend || 0, previousData.spend || 0),
                cpm: createMetricWithDelta(currentData.cpm || 0, previousData.cpm || 0),
                impressions: createMetricWithDelta(currentData.impressions || 0, previousData.impressions || 0),
                reach: createMetricWithDelta(currentData.reach || 0, previousData.reach || 0),
                clicks: createMetricWithDelta(currentData.clicks || 0, previousData.clicks || 0),
                ctr: createMetricWithDelta(currentData.ctr || 0, previousData.ctr || 0),
                cpc: createMetricWithDelta(currentData.cpc || 0, previousData.cpc || 0),
                conversions: createMetricWithDelta(currentData.conversions || 0, previousData.conversions || 0),
                convRate: createMetricWithDelta(
                    currentData.clicks > 0 ? (currentData.conversions / currentData.clicks) * 100 : 0,
                    previousData.clicks > 0 ? (previousData.conversions / previousData.clicks) * 100 : 0
                ),
                cpa: createMetricWithDelta(currentData.cpa || 0, previousData.cpa || 0),
                roas: createMetricWithDelta(currentData.roas || 0, previousData.roas || 0),
            });

        } catch (error) {
            console.error('Failed to set KPI metrics:', error);
        }
    };

    // Fetch channel comparison data for year-over-year analysis
    const fetchChannelComparison = useCallback(async () => {
        if (!activeTab || activeTab !== 'performance') return;

        setChannelCompLoading(true);
        try {
            const metrics = ['spend', 'impressions', 'clicks', 'conversions'];

            // Helper to fetch data for a specific year
            const fetchYearData = async (year: number) => {
                const results: Record<string, Record<string, number>> = {};

                for (const metric of metrics) {
                    const params = new URLSearchParams({
                        x_axis: 'channel',
                        y_axis: metric,
                        year: String(year),
                    });

                    // Add active filters
                    if (filters.platforms && filters.platforms.length > 0) {
                        params.set('platforms', filters.platforms.join(','));
                    }
                    if (filters.regions && filters.regions.length > 0) {
                        params.set('regions', filters.regions.join(','));
                    }
                    if (filters.devices && filters.devices.length > 0) {
                        params.set('devices', filters.devices.join(','));
                    }
                    if (filters.funnelStages && filters.funnelStages.length > 0) {
                        params.set('funnels', filters.funnelStages.join(','));
                    }

                    const res: any = await api.get(`/campaigns/chart-data?${params}`);
                    const items = res.data || [];

                    items.forEach((item: any) => {
                        const channel = item.name || 'Unknown';
                        if (!results[channel]) {
                            results[channel] = { spend: 0, impressions: 0, clicks: 0, conversions: 0 };
                        }
                        results[channel][metric] = item.value || 0;
                    });
                }
                return results;
            };

            // Fetch data for both years in parallel
            const [year1Data, year2Data] = await Promise.all([
                fetchYearData(channelCompYear1),
                fetchYearData(channelCompYear2)
            ]);

            // Get all unique channels from both years
            const allChannels = new Set([...Object.keys(year1Data), ...Object.keys(year2Data)]);

            // Build comparison data using actual year data
            const compData = Array.from(allChannels).map(channel => {
                const data1 = year1Data[channel] || { spend: 0, impressions: 0, clicks: 0, conversions: 0, revenue: 0 };
                const data2 = year2Data[channel] || { spend: 0, impressions: 0, clicks: 0, conversions: 0, revenue: 0 };

                // Year 1 metrics
                const spend2025 = data1.spend;
                const impressions2025 = data1.impressions;
                const clicks2025 = data1.clicks;
                const conversions2025 = data1.conversions;
                const revenue2025 = data1.revenue || 0;
                const ctr2025 = impressions2025 > 0 ? (clicks2025 / impressions2025) * 100 : 0;
                const cpa2025 = conversions2025 > 0 ? spend2025 / conversions2025 : 0;
                const roas2025 = spend2025 > 0 ? (revenue2025 / spend2025) : 0;

                // Year 2 metrics
                const spend2024 = data2.spend;
                const impressions2024 = data2.impressions;
                const clicks2024 = data2.clicks;
                const conversions2024 = data2.conversions;
                const revenue2024 = data2.revenue || 0;
                const ctr2024 = impressions2024 > 0 ? (clicks2024 / impressions2024) * 100 : 0;
                const cpa2024 = conversions2024 > 0 ? spend2024 / conversions2024 : 0;
                const roas2024 = spend2024 > 0 ? (revenue2024 / spend2024) : 0;

                // Calculate % changes (positive = improvement in year1 vs year2)
                const calcChange = (current: number, previous: number) =>
                    previous > 0 ? ((current - previous) / previous) * 100 : 0;

                return {
                    channel,
                    spend2025,
                    spend2024,
                    spendChange: calcChange(spend2025, spend2024),
                    ctr2025,
                    ctr2024,
                    ctrChange: calcChange(ctr2025, ctr2024),
                    conversions2025,
                    conversions2024,
                    conversionsChange: calcChange(conversions2025, conversions2024),
                    cpa2025,
                    cpa2024,
                    cpaChange: calcChange(cpa2024, cpa2025), // Lower CPA is better, so reverse
                    roas2025,
                    roas2024,
                    roasChange: calcChange(roas2025, roas2024),
                };
            }).filter(row => row.spend2025 > 0 || row.spend2024 > 0) // Only show channels with data
                .sort((a, b) => b.spend2025 - a.spend2025);

            setChannelCompData(compData);
        } catch (error) {
            console.error('Failed to fetch channel comparison:', error);
        } finally {
            setChannelCompLoading(false);
        }
    }, [activeTab, channelCompYear1, channelCompYear2, filters.platforms, filters.regions, filters.devices, filters.funnelStages]);

    const fetchFilterOptions = async () => {
        try {
            console.log('Calling fetchFilterOptions (/campaigns/filters)...');
            const filterOptions: any = await api.get('/campaigns/filters');
            console.log('Filter options from API response:', filterOptions);

            if (filterOptions.platforms) setAvailablePlatforms(filterOptions.platforms);
            if (filterOptions.funnel_stages) setAvailableFunnelStages(filterOptions.funnel_stages);
            if (filterOptions.channels) setAvailableChannels(filterOptions.channels);
            if (filterOptions.devices) setAvailableDevices(filterOptions.devices);
            if (filterOptions.placements) setAvailablePlacements(filterOptions.placements);
            if (filterOptions.regions) setAvailableRegions(filterOptions.regions);
            if (filterOptions.ad_types) setAvailableAdTypes(filterOptions.ad_types);

            // Handle any extra dynamic filters if they exist
            // (These could be mapped to a generic 'Extra Filters' section if needed)
        } catch (error) {
            console.error('Failed to fetch filter options:', error);
        }
    };

    const applyFilters = () => {
        // React Query handles refetching automatically
    };

    const resetFilters = () => {
        setFilters({
            platforms: [],
            funnelStages: [],
            channels: [],
            devices: [],
            placements: [],
            regions: [],
            adTypes: [],
            dateRange: undefined
        });
    };

    const handleDrillDown = (dimension: string, value: string) => {
        setDrillDownData({
            dimension,
            value,
            data: channelData.length > 0 ? channelData : platformData
        });
        setDrillDownOpen(true);
    };

    const handleBrushChange = (startIndex: number, endIndex: number) => {
        if (trendData[startIndex] && trendData[endIndex]) {
            setSelectedDateRange({
                start: trendData[startIndex].date,
                end: trendData[endIndex].date
            });
        }
    };

    const formatNumber = (num: number) => {
        if (num >= 1000000) return (num / 1000000).toFixed(2) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(1) + 'k';
        return num.toFixed(0);
    };

    // Derived data for new charts
    const funnelData = useMemo(() => [
        { stage: 'Impressions', value: kpis.impressions, color: '#3b82f6' },
        { stage: 'Clicks', value: kpis.clicks, color: '#8b5cf6' },
        { stage: 'Conversions', value: kpis.conversions, color: '#10b981' }
    ], [kpis]);

    // Compute funnel stage performance data for table
    const funnelStageData = useMemo(() => {
        if (!funnelStageDataFromBackend || funnelStageDataFromBackend.length === 0) return [];

        return funnelStageDataFromBackend.map((stage: any) => ({
            funnel: stage.funnel || stage.name || 'Unknown',
            spend: stage.spend || 0,
            impressions: stage.impressions || 0,
            reach: stage.reach || 0,
            cpm: stage.cpm || (stage.impressions > 0 ? (stage.spend / stage.impressions * 1000) : 0),
            clicks: stage.clicks || 0,
            ctr: stage.ctr || (stage.impressions > 0 ? (stage.clicks / stage.impressions * 100) : 0),
            cpc: stage.cpc || (stage.clicks > 0 ? (stage.spend / stage.clicks) : 0),
            conversions: stage.conversions || 0,
            cpa: stage.cpa || (stage.conversions > 0 ? (stage.spend / stage.conversions) : 0),
            roas: stage.roas || (stage.spend > 0 ? ((stage.revenue || 0) / stage.spend) : 0)
        }));
    }, [funnelStageDataFromBackend]);

    // Filter channel data by selected funnel stage
    const filteredChannelData = useMemo(() => {
        if (!channelByFunnelData || channelByFunnelData.length === 0) {
            return channelData; // Fallback to unfiltered
        }

        if (selectedFunnelStage) {
            // Filter by selected funnel stage (when user clicks a funnel stage row)
            return channelByFunnelData.filter((item: any) => item.funnel === selectedFunnelStage);
        } else {

            // Aggregate across all funnel stages
            const channelTotals: { [key: string]: any } = {};
            channelByFunnelData.forEach((item: any) => {
                if (!channelTotals[item.channel]) {
                    channelTotals[item.channel] = {
                        channel: item.channel,
                        spend: 0,
                        impressions: 0,
                        reach: 0,
                        clicks: 0,
                        conversions: 0,
                        revenue: 0
                    };
                }
                channelTotals[item.channel].spend += item.spend || 0;
                channelTotals[item.channel].impressions += item.impressions || 0;
                channelTotals[item.channel].reach += item.reach || 0;
                channelTotals[item.channel].clicks += item.clicks || 0;
                channelTotals[item.channel].conversions += item.conversions || 0;
                channelTotals[item.channel].revenue += item.revenue || 0;
            });

            // Recalculate derived metrics
            return Object.values(channelTotals).map((ch: any) => ({
                ...ch,
                ctr: ch.impressions > 0 ? (ch.clicks / ch.impressions * 100) : 0,
                cpc: ch.clicks > 0 ? (ch.spend / ch.clicks) : 0,
                cpm: ch.impressions > 0 ? (ch.spend / ch.impressions * 1000) : 0,
                cpa: ch.conversions > 0 ? (ch.spend / ch.conversions) : 0,
                roas: ch.spend > 0 ? ((ch.revenue || 0) / ch.spend) : 0
            })).sort((a, b) => b.spend - a.spend);
        }
    }, [channelByFunnelData, selectedFunnelStage, channelData]);



    const scorecardData = useMemo(() => platformData.map(p => {
        const metrics = [];
        if (dataAvailability.metrics.roas) {
            metrics.push({ label: 'ROAS', value: `${(p.roas || 0).toFixed(2)}x` });
        }
        metrics.push({ label: 'CTR', value: `${(p.ctr || 0).toFixed(2)}%` });

        return {
            name: p.name,
            score: dataAvailability.metrics.roas
                ? Math.min(100, Math.round((p.roas || 0) * 30 + (p.ctr || 0) * 10))
                : Math.min(100, Math.round((p.ctr || 0) * 40)), // Adjust weight if ROAS missing
            metrics
        };
    }), [platformData, dataAvailability.metrics.roas]);

    const bulletData = useMemo(() => {
        const data = [
            { label: 'Spend', value: kpis.spend, target: kpis.spend * 1.2, ranges: [kpis.spend * 0.5, kpis.spend * 0.8, kpis.spend * 1.1] as [number, number, number] },
            { label: 'Conversions', value: kpis.conversions, target: kpis.conversions * 1.3, ranges: [kpis.conversions * 0.4, kpis.conversions * 0.7, kpis.conversions * 1.0] as [number, number, number] },
        ];

        if (dataAvailability.metrics.roas) {
            data.push({ label: 'ROAS', value: kpis.roas, target: 3, ranges: [1, 2, 2.5] as [number, number, number] });
        }

        return data;
    }, [kpis, dataAvailability.metrics.roas]);

    const sparklineItems = useMemo(() => {
        const items = [
            { label: 'Spend', value: kpis.spend, prefix: '$', trend: trendData, trendKey: 'spend', change: 12.5 },
            { label: 'Clicks', value: kpis.clicks, trend: trendData, trendKey: 'clicks', change: 8.2 },
            { label: 'CTR', value: kpis.ctr, suffix: '%', trend: trendData, trendKey: 'ctr', change: -2.1 },
            { label: 'CPC', value: kpis.cpc, prefix: '$', trend: trendData, trendKey: 'cpc', change: 5.8 },
            { label: 'Conversions', value: kpis.conversions, trend: trendData, trendKey: 'conversions', change: 15.3 },
        ];

        if (dataAvailability.metrics.roas) {
            items.push({ label: 'ROAS', value: kpis.roas, suffix: 'x', trend: trendData, trendKey: 'roas', change: 7.1 });
        }

        return items;
    }, [kpis, trendData, dataAvailability.metrics.roas]);



    if (loading) {
        return (
            <div className="flex h-screen items-center justify-center">
                <motion.div
                    className="flex flex-col items-center gap-4"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                >
                    <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
                    <p className="text-muted-foreground">Loading dashboard...</p>
                </motion.div>
            </div>
        );
    }

    return (
        <div className="space-y-6 p-6 mx-auto">
            {/* Main Content Area */}
            <div className="space-y-6">
                {/* Header */}
                <motion.div
                    className="flex items-center justify-between"
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                >
                    <div>
                        <h1 className="text-3xl font-bold flex items-center gap-2">
                            <Sparkles className="h-7 w-7 text-primary" />
                            Executive Overview
                        </h1>
                        <p className="text-muted-foreground">High-level performance insights</p>
                    </div>

                </motion.div>

                {/* Simple KPI Cards - All Metrics in Single Line */}
                <motion.div
                    className="grid gap-3 grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-9"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                >
                    {(() => {
                        // Use dashboardStats.summary_groups.current for consistency with bottom KPI cards
                        const stats = dashboardStats?.summary_groups?.current || {};
                        const spend = stats.spend || 0;
                        const conversions = stats.conversions || 0;
                        const impressions = stats.impressions || 0;
                        const clicks = stats.clicks || 0;
                        const ctr = stats.ctr || (impressions > 0 ? (clicks / impressions * 100) : 0);
                        const cpa = conversions > 0 ? (spend / conversions) : 0;
                        const convRate = clicks > 0 ? ((conversions / clicks) * 100) : 0;
                        const cpc = stats.cpc || (clicks > 0 ? (spend / clicks) : 0);
                        const roas = stats.roas || 0;

                        return (
                            <>
                                <Card className="p-3">
                                    <p className="text-xs text-muted-foreground">Spend</p>
                                    <p className="text-xl font-bold text-blue-500">${formatNumber(spend)}</p>
                                </Card>
                                <Card className="p-3">
                                    <p className="text-xs text-muted-foreground">Conversions</p>
                                    <p className="text-xl font-bold text-purple-500">{formatNumber(conversions)}</p>
                                </Card>
                                <Card className="p-3">
                                    <p className="text-xs text-muted-foreground">Impressions</p>
                                    <p className="text-xl font-bold text-cyan-500">{formatNumber(impressions)}</p>
                                </Card>
                                <Card className="p-3">
                                    <p className="text-xs text-muted-foreground">Clicks</p>
                                    <p className="text-xl font-bold text-green-500">{formatNumber(clicks)}</p>
                                </Card>
                                <Card className="p-3">
                                    <p className="text-xs text-muted-foreground">CTR</p>
                                    <p className="text-xl font-bold text-orange-500">{ctr.toFixed(2)}%</p>
                                </Card>
                                <Card className="p-3">
                                    <p className="text-xs text-muted-foreground">CPA</p>
                                    <p className="text-xl font-bold text-pink-500">${cpa.toFixed(2)}</p>
                                </Card>
                                <Card className="p-3">
                                    <p className="text-xs text-muted-foreground">Conv Rate</p>
                                    <p className="text-xl font-bold text-emerald-500">{convRate.toFixed(2)}%</p>
                                </Card>
                                <Card className="p-3">
                                    <p className="text-xs text-muted-foreground">CPC</p>
                                    <p className="text-xl font-bold text-indigo-500">${cpc.toFixed(2)}</p>
                                </Card>
                                <Card className="p-3">
                                    <p className="text-xs text-muted-foreground">ROAS</p>
                                    <p className="text-xl font-bold text-amber-500">{roas.toFixed(2)}x</p>
                                </Card>
                            </>
                        );
                    })()}
                </motion.div>


                {/* Executive Filters Content Area */}
                <Card className="border-white/10 bg-black/20 backdrop-blur-sm">
                    <CardHeader className="pb-3 border-b border-white/5">
                        <div className="flex items-center gap-2">
                            <Filter className="h-5 w-5 text-primary" />
                            <CardTitle className="text-xl">Executive Filters</CardTitle>
                        </div>
                        <CardDescription>Filter data across all views</CardDescription>
                    </CardHeader>
                    <CardContent className="pt-6">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            {dataAvailability.filters.platform && (
                                <div className="space-y-2">
                                    <Label className="text-sm font-medium">Platform</Label>
                                    <MultiSelect
                                        options={platformOptions}
                                        selected={filters.platforms}
                                        onChange={(selected) => setFilters({ ...filters, platforms: selected })}
                                        placeholder="All Platforms"
                                        className="w-full"
                                    />
                                </div>
                            )}

                            <div className="space-y-2">
                                <Label className="text-sm font-medium">Date Range</Label>
                                <DateRangePicker
                                    date={filters.dateRange}
                                    onDateChange={(range) => setFilters({ ...filters, dateRange: range })}
                                />
                            </div>

                            {dataAvailability.filters.channel && (
                                <div className="space-y-2">
                                    <Label className="text-sm font-medium">Channel</Label>
                                    <MultiSelect
                                        options={channelOptions}
                                        selected={filters.channels}
                                        onChange={(selected) => setFilters({ ...filters, channels: selected })}
                                        placeholder="All Channels"
                                        className="w-full"
                                    />
                                </div>
                            )}

                            {dataAvailability.filters.funnel && (
                                <div className="space-y-2">
                                    <Label className="text-sm font-medium">Funnel Stage</Label>
                                    <MultiSelect
                                        options={funnelOptions}
                                        selected={filters.funnelStages}
                                        onChange={(selected) => setFilters({ ...filters, funnelStages: selected })}
                                        placeholder="All Stages"
                                        className="w-full"
                                    />
                                </div>
                            )}

                            {dataAvailability.filters.device && (
                                <div className="space-y-2">
                                    <Label className="text-sm font-medium">Device</Label>
                                    <MultiSelect
                                        options={deviceOptions}
                                        selected={filters.devices}
                                        onChange={(selected) => setFilters({ ...filters, devices: selected })}
                                        placeholder="All Devices"
                                        className="w-full"
                                    />
                                </div>
                            )}

                            {dataAvailability.filters.adType && (
                                <div className="space-y-2">
                                    <Label className="text-sm font-medium">Ad Type</Label>
                                    <MultiSelect
                                        options={adTypeOptions}
                                        selected={filters.adTypes}
                                        onChange={(selected) => setFilters({ ...filters, adTypes: selected })}
                                        placeholder="All Ad Types"
                                        className="w-full"
                                    />
                                </div>
                            )}

                            {dataAvailability.filters.placement && (
                                <div className="space-y-2">
                                    <Label className="text-sm font-medium">Placement</Label>
                                    <MultiSelect
                                        options={placementOptions}
                                        selected={filters.placements}
                                        onChange={(selected) => setFilters({ ...filters, placements: selected })}
                                        placeholder="All Placements"
                                        className="w-full"
                                    />
                                </div>
                            )}

                            {dataAvailability.filters.region && (
                                <div className="space-y-2">
                                    <Label className="text-sm font-medium">Region</Label>
                                    <MultiSelect
                                        options={regionOptions}
                                        selected={filters.regions}
                                        onChange={(selected) => setFilters({ ...filters, regions: selected })}
                                        placeholder="All Regions"
                                        className="w-full"
                                    />
                                </div>
                            )}

                            <div className="flex items-end gap-2">
                                <Button
                                    onClick={resetFilters}
                                    variant="outline"
                                    className="flex-1 gap-2 border-gray-600 text-gray-300 hover:bg-gray-700"
                                >
                                    <RotateCcw className="h-4 w-4" />
                                    Reset
                                </Button>
                                <Button onClick={applyFilters} className="flex-1 gap-2 bg-primary/20 hover:bg-primary/30 border-primary/30 text-primary">
                                    <Filter className="h-4 w-4" />
                                    Apply Filters
                                </Button>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* Tabs */}
                <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
                    <TabsList className="grid w-full grid-cols-6">
                        <TabsTrigger value="overview" className="gap-2">
                            <LayoutGrid className="h-4 w-4" />
                            Overview
                        </TabsTrigger>
                        <TabsTrigger value="channel" className="gap-2">
                            <BarChart3 className="h-4 w-4" />
                            Channel
                        </TabsTrigger>
                        <TabsTrigger value="platform" className="gap-2">
                            <Layers className="h-4 w-4" />
                            Platform
                        </TabsTrigger>
                        <TabsTrigger value="other" className="gap-2">
                            <Box className="h-4 w-4" />
                            Other
                        </TabsTrigger>
                        <TabsTrigger value="funnel" className="gap-2">
                            <Filter className="h-4 w-4" />
                            Funnel
                        </TabsTrigger>
                        <TabsTrigger value="performance" className="gap-2">
                            <Award className="h-4 w-4" />
                            Performance
                        </TabsTrigger>
                    </TabsList>

                    {/* Overview Tab */}
                    <TabsContent value="overview" className="space-y-6">
                        <AnimatePresence mode="wait">
                            <motion.div
                                key="overview"
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -20 }}
                                className="space-y-6"
                            >
                                {/* NEW: KPI Spark Groups */}
                                {/* NEW: KPI Cards with Sparklines */}
                                {trendData.length > 0 && (
                                    <KpiSparkGroups
                                        data={{
                                            current: {
                                                // Prioritize dashboardStats for accurate combined metrics spanning full date range
                                                spend: dashboardStats.summary_groups?.current?.spend ?? trendData.reduce((sum, d) => sum + (d.spend || 0), 0),
                                                impressions: dashboardStats.summary_groups?.current?.impressions ?? trendData.reduce((sum, d) => sum + (d.impressions || 0), 0),
                                                clicks: dashboardStats.summary_groups?.current?.clicks ?? trendData.reduce((sum, d) => sum + (d.clicks || 0), 0),
                                                conversions: dashboardStats.summary_groups?.current?.conversions ?? trendData.reduce((sum, d) => sum + (d.conversions || 0), 0),
                                                reach: dashboardStats.summary_groups?.current?.reach ?? trendData.reduce((sum, d) => sum + (d.reach || 0), 0),
                                                revenue: dashboardStats.summary_groups?.current?.revenue ?? trendData.reduce((sum, d) => sum + (d.revenue || 0), 0),
                                                cpm: dashboardStats.summary_groups?.current?.cpm ?? (trendData.reduce((sum, d) => sum + (d.impressions || 0), 0) > 0 ? trendData.reduce((sum, d) => sum + (d.spend || 0), 0) / trendData.reduce((sum, d) => sum + (d.impressions || 0), 0) * 1000 : 0),
                                                ctr: dashboardStats.summary_groups?.current?.ctr ?? (trendData.reduce((sum, d) => sum + (d.impressions || 0), 0) > 0 ? trendData.reduce((sum, d) => sum + (d.clicks || 0), 0) / trendData.reduce((sum, d) => sum + (d.impressions || 0), 0) * 100 : 0),
                                                cpc: dashboardStats.summary_groups?.current?.cpc ?? (trendData.reduce((sum, d) => sum + (d.clicks || 0), 0) > 0 ? trendData.reduce((sum, d) => sum + (d.spend || 0), 0) / trendData.reduce((sum, d) => sum + (d.clicks || 0), 0) : 0),
                                                cpa: dashboardStats.summary_groups?.current?.cpa ?? (trendData.reduce((sum, d) => sum + (d.conversions || 0), 0) > 0 ? trendData.reduce((sum, d) => sum + (d.spend || 0), 0) / trendData.reduce((sum, d) => sum + (d.conversions || 0), 0) : 0),
                                                roas: dashboardStats.summary_groups?.current?.roas ?? (trendData.reduce((sum, d) => sum + (d.spend || 0), 0) > 0 ? (trendData.reduce((sum, d) => sum + (d.revenue || 0), 0)) / trendData.reduce((sum, d) => sum + (d.spend || 0), 0) : 0)
                                            },
                                            previous: dashboardStats.summary_groups?.previous || {
                                                spend: 0, impressions: 0, clicks: 0, conversions: 0,
                                                cpm: 0, ctr: 0, cpc: 0, cpa: 0, roas: 0, reach: 0
                                            },
                                            sparkline: trendData.map(d => ({
                                                date: d.date,
                                                spend: d.spend || 0,
                                                clicks: d.clicks || 0,
                                                conversions: d.conversions || 0,
                                                revenue: d.revenue || 0
                                            }))
                                        }}
                                        schema={schema || undefined}
                                    />
                                )}


                                {/* WEEKLY PERFORMANCE TRENDS - Dynamic rendering based on available metrics */}
                                {dataAvailability.hasAnyData && monthlyTrendData.length > 0 && (
                                    <Card data-testid="chart-trends-card">
                                        <CardHeader>
                                            <CardTitle className="flex items-center gap-2">
                                                <TrendingUp className="h-5 w-5" />
                                                Monthly Performance Trends
                                            </CardTitle>
                                            <CardDescription>Hover for more details</CardDescription>
                                        </CardHeader>
                                        <CardContent className="space-y-4">
                                            {/* Chart 1: Spend with CTR overlay */}
                                            {dataAvailability.metrics.spend && dataAvailability.metrics.ctr && (
                                                <div className="h-[150px]" data-testid="chart-spend-ctr">
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <span className="text-xs font-medium text-muted-foreground w-16">Spend</span>
                                                        <div className="flex gap-3 text-xs">
                                                            <span className="flex items-center gap-1"><span className="w-3 h-3 bg-teal-500 rounded-sm"></span> Spend</span>
                                                            <span className="flex items-center gap-1"><span className="w-3 h-3 bg-orange-400 rounded-sm"></span> CTR</span>
                                                        </div>
                                                    </div>
                                                    <ResponsiveContainer width="100%" height="100%">
                                                        <ComposedChart data={monthlyTrendData}>
                                                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
                                                            <XAxis dataKey="date" tick={{ fill: '#9ca3af', fontSize: 9 }} angle={-45} textAnchor="end" height={50} />
                                                            <YAxis yAxisId="left" tick={{ fill: '#9ca3af', fontSize: 10 }} tickFormatter={(v) => `$${v >= 1000 ? (v / 1000).toFixed(0) + 'k' : v}`} domain={['auto', 'auto']} />
                                                            <YAxis yAxisId="right" orientation="right" tick={{ fill: '#9ca3af', fontSize: 10 }} tickFormatter={(v) => `${v.toFixed(2)}%`} domain={[(dataMin: number) => dataMin * 0.8, (dataMax: number) => dataMax * 1.2]} />
                                                            <Bar yAxisId="left" dataKey="spend" fill="#14b8a6" radius={[2, 2, 0, 0]} />
                                                            <Line yAxisId="right" type="monotone" dataKey="ctr" stroke="#fb923c" strokeWidth={2} dot={false} />
                                                        </ComposedChart>
                                                    </ResponsiveContainer>
                                                </div>
                                            )}

                                            {/* Chart 2: Spend with Conversions overlay */}
                                            {dataAvailability.metrics.spend && dataAvailability.metrics.conversions && (
                                                <div className="h-[150px]" data-testid="chart-spend-conversions">
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <span className="text-xs font-medium text-muted-foreground w-16">Spend</span>
                                                        <div className="flex gap-3 text-xs">
                                                            <span className="flex items-center gap-1"><span className="w-3 h-3 bg-blue-500 rounded-sm"></span> Spend</span>
                                                            <span className="flex items-center gap-1"><span className="w-3 h-3 bg-purple-400 rounded-sm"></span> Conversions</span>
                                                        </div>
                                                    </div>
                                                    <ResponsiveContainer width="100%" height="100%">
                                                        <ComposedChart data={monthlyTrendData}>
                                                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
                                                            <XAxis dataKey="date" tick={{ fill: '#9ca3af', fontSize: 9 }} angle={-45} textAnchor="end" height={50} />
                                                            <YAxis yAxisId="left" tick={{ fill: '#9ca3af', fontSize: 10 }} tickFormatter={(v) => `$${v >= 1000 ? (v / 1000).toFixed(0) + 'k' : v}`} domain={['auto', 'auto']} />
                                                            <YAxis yAxisId="right" orientation="right" tick={{ fill: '#9ca3af', fontSize: 10 }} domain={[(dataMin: number) => Math.floor(dataMin * 0.8), (dataMax: number) => Math.ceil(dataMax * 1.2)]} />
                                                            <Bar yAxisId="left" dataKey="spend" fill="#3b82f6" radius={[2, 2, 0, 0]} />
                                                            <Line yAxisId="right" type="monotone" dataKey="conversions" stroke="#a78bfa" strokeWidth={2} dot={false} />
                                                        </ComposedChart>
                                                    </ResponsiveContainer>
                                                </div>
                                            )}

                                            {/* Chart 3: Spend with ROAS overlay - only show if ROAS can be calculated */}
                                            {dataAvailability.metrics.spend && dataAvailability.metrics.roas && (
                                                <div className="h-[150px]" data-testid="chart-spend-roas">
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <span className="text-xs font-medium text-muted-foreground w-16">Spend</span>
                                                        <div className="flex gap-3 text-xs">
                                                            <span className="flex items-center gap-1"><span className="w-3 h-3 bg-indigo-500 rounded-sm"></span> Spend</span>
                                                            <span className="flex items-center gap-1"><span className="w-3 h-3 bg-yellow-400 rounded-sm"></span> ROAS</span>
                                                        </div>
                                                    </div>
                                                    <ResponsiveContainer width="100%" height="100%">
                                                        <ComposedChart data={monthlyTrendData}>
                                                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
                                                            <XAxis dataKey="date" tick={{ fill: '#9ca3af', fontSize: 9 }} angle={-45} textAnchor="end" height={50} />
                                                            <YAxis yAxisId="left" tick={{ fill: '#9ca3af', fontSize: 10 }} tickFormatter={(v) => `$${v >= 1000 ? (v / 1000).toFixed(0) + 'k' : v}`} domain={['auto', 'auto']} />
                                                            <YAxis yAxisId="right" orientation="right" tick={{ fill: '#9ca3af', fontSize: 10 }} tickFormatter={(v) => `${v.toFixed(1)}x`} domain={[(dataMin: number) => Math.max(0, dataMin * 0.7), (dataMax: number) => dataMax * 1.3]} />
                                                            <Bar yAxisId="left" dataKey="spend" fill="#6366f1" radius={[2, 2, 0, 0]} />
                                                            <Line yAxisId="right" type="monotone" dataKey="roas" stroke="#facc15" strokeWidth={2} dot={false} />
                                                        </ComposedChart>
                                                    </ResponsiveContainer>
                                                </div>
                                            )}

                                            {/* Chart 4: Conversions with CPA overlay */}
                                            {dataAvailability.metrics.conversions && dataAvailability.metrics.cpa && (
                                                <div className="h-[150px]" data-testid="chart-conversions-cpa">
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <span className="text-xs font-medium text-muted-foreground w-16">Conv</span>
                                                        <div className="flex gap-3 text-xs">
                                                            <span className="flex items-center gap-1"><span className="w-3 h-3 bg-pink-500 rounded-sm"></span> Conversions</span>
                                                            <span className="flex items-center gap-1"><span className="w-3 h-3 bg-emerald-400 rounded-sm"></span> CPA</span>
                                                        </div>
                                                    </div>
                                                    <ResponsiveContainer width="100%" height="100%">
                                                        <ComposedChart data={monthlyTrendData}>
                                                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
                                                            <XAxis dataKey="date" tick={{ fill: '#9ca3af', fontSize: 9 }} angle={-45} textAnchor="end" height={50} />
                                                            <YAxis yAxisId="left" tick={{ fill: '#9ca3af', fontSize: 10 }} tickFormatter={(v) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v} domain={['auto', 'auto']} />
                                                            <YAxis yAxisId="right" orientation="right" tick={{ fill: '#9ca3af', fontSize: 10 }} tickFormatter={(v) => `$${v.toFixed(0)}`} domain={[(dataMin: number) => Math.floor(dataMin * 0.8), (dataMax: number) => Math.ceil(dataMax * 1.2)]} />
                                                            <Bar yAxisId="left" dataKey="conversions" fill="#ec4899" radius={[2, 2, 0, 0]} />
                                                            <Line yAxisId="right" type="monotone" dataKey="costPerConv" stroke="#34d399" strokeWidth={2} dot={false} />
                                                        </ComposedChart>
                                                    </ResponsiveContainer>
                                                </div>
                                            )}

                                            {/* Chart 5: Clicks with CTR overlay */}
                                            {dataAvailability.metrics.clicks && dataAvailability.metrics.ctr && (
                                                <div className="h-[150px]" data-testid="chart-clicks-ctr">
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <span className="text-xs font-medium text-muted-foreground w-16">Clicks</span>
                                                        <div className="flex gap-3 text-xs">
                                                            <span className="flex items-center gap-1"><span className="w-3 h-3 bg-amber-500 rounded-sm"></span> Clicks</span>
                                                            <span className="flex items-center gap-1"><span className="w-3 h-3 bg-cyan-400 rounded-sm"></span> CTR</span>
                                                        </div>
                                                    </div>
                                                    <ResponsiveContainer width="100%" height="100%">
                                                        <ComposedChart data={monthlyTrendData}>
                                                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
                                                            <XAxis dataKey="date" tick={{ fill: '#9ca3af', fontSize: 9 }} angle={-45} textAnchor="end" height={50} />
                                                            <YAxis yAxisId="left" tick={{ fill: '#9ca3af', fontSize: 10 }} tickFormatter={(v) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v} domain={['auto', 'auto']} />
                                                            <YAxis yAxisId="right" orientation="right" tick={{ fill: '#9ca3af', fontSize: 10 }} tickFormatter={(v) => `${v.toFixed(2)}%`} domain={[(dataMin: number) => dataMin * 0.8, (dataMax: number) => dataMax * 1.2]} />
                                                            <Bar yAxisId="left" dataKey="clicks" fill="#f59e0b" radius={[2, 2, 0, 0]} />
                                                            <Line yAxisId="right" type="monotone" dataKey="ctr" stroke="#22d3ee" strokeWidth={2} dot={false} />
                                                        </ComposedChart>
                                                    </ResponsiveContainer>
                                                </div>
                                            )}

                                            {/* Chart 6: Clicks with CPC overlay */}
                                            {dataAvailability.metrics.clicks && dataAvailability.metrics.cpc && (
                                                <div className="h-[150px]" data-testid="chart-clicks-cpc">
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <span className="text-xs font-medium text-muted-foreground w-16">Clicks</span>
                                                        <div className="flex gap-3 text-xs">
                                                            <span className="flex items-center gap-1"><span className="w-3 h-3 bg-amber-500 rounded-sm"></span> Clicks</span>
                                                            <span className="flex items-center gap-1"><span className="w-3 h-3 bg-cyan-400 rounded-sm"></span> CPC</span>
                                                        </div>
                                                    </div>
                                                    <ResponsiveContainer width="100%" height="100%">
                                                        <ComposedChart data={monthlyTrendData}>
                                                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
                                                            <XAxis dataKey="date" tick={{ fill: '#9ca3af', fontSize: 9 }} angle={-45} textAnchor="end" height={50} />
                                                            <YAxis yAxisId="left" tick={{ fill: '#9ca3af', fontSize: 10 }} tickFormatter={(v) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v} domain={['auto', 'auto']} />
                                                            <YAxis yAxisId="right" orientation="right" tick={{ fill: '#9ca3af', fontSize: 10 }} tickFormatter={(v) => `$${v.toFixed(2)}`} domain={[(dataMin: number) => dataMin * 0.8, (dataMax: number) => dataMax * 1.2]} />
                                                            <Bar yAxisId="left" dataKey="clicks" fill="#f59e0b" radius={[2, 2, 0, 0]} />
                                                            <Line yAxisId="right" type="monotone" dataKey="cpc" stroke="#22d3ee" strokeWidth={2} dot={false} />
                                                        </ComposedChart>
                                                    </ResponsiveContainer>
                                                </div>
                                            )}

                                            {/* Chart 7: Clicks with Cumulative Conversions overlay */}
                                            {dataAvailability.metrics.clicks && dataAvailability.metrics.conversions && (
                                                <div className="h-[150px]" data-testid="chart-clicks-conversions">
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <span className="text-xs font-medium text-muted-foreground w-16">Clicks</span>
                                                        <div className="flex gap-3 text-xs">
                                                            <span className="flex items-center gap-1"><span className="w-3 h-3 bg-amber-500 rounded-sm"></span> Clicks</span>
                                                            <span className="flex items-center gap-1"><span className="w-3 h-3 bg-purple-400 rounded-sm"></span> Conversions</span>
                                                        </div>
                                                    </div>
                                                    <ResponsiveContainer width="100%" height="100%">
                                                        <ComposedChart data={monthlyTrendData}>
                                                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
                                                            <XAxis dataKey="date" tick={{ fill: '#9ca3af', fontSize: 9 }} angle={-45} textAnchor="end" height={50} />
                                                            <YAxis yAxisId="left" tick={{ fill: '#9ca3af', fontSize: 10 }} tickFormatter={(v) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v} domain={['auto', 'auto']} />
                                                            <YAxis yAxisId="right" orientation="right" tick={{ fill: '#9ca3af', fontSize: 10 }} tickFormatter={(v) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v} domain={[(dataMin: number) => Math.floor(dataMin * 0.8), (dataMax: number) => Math.ceil(dataMax * 1.2)]} />
                                                            <Bar yAxisId="left" dataKey="clicks" fill="#f59e0b" radius={[2, 2, 0, 0]} />
                                                            <Line yAxisId="right" type="monotone" dataKey="conversions" stroke="#a78bfa" strokeWidth={2} dot={false} />
                                                        </ComposedChart>
                                                    </ResponsiveContainer>
                                                </div>
                                            )}

                                            {/* Chart 8: Impressions with Cumulative Clicks overlay */}
                                            {dataAvailability.metrics.impressions && dataAvailability.metrics.clicks && (
                                                <div className="h-[150px]" data-testid="chart-impressions-clicks">
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <span className="text-xs font-medium text-muted-foreground w-16">Impr</span>
                                                        <div className="flex gap-3 text-xs">
                                                            <span className="flex items-center gap-1"><span className="w-3 h-3 bg-slate-500 rounded-sm"></span> Impressions</span>
                                                            <span className="flex items-center gap-1"><span className="w-3 h-3 bg-amber-400 rounded-sm"></span> Clicks</span>
                                                        </div>
                                                    </div>
                                                    <ResponsiveContainer width="100%" height="100%">
                                                        <ComposedChart data={monthlyTrendData}>
                                                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
                                                            <XAxis dataKey="date" tick={{ fill: '#9ca3af', fontSize: 9 }} angle={-45} textAnchor="end" height={50} />
                                                            <YAxis yAxisId="left" tick={{ fill: '#9ca3af', fontSize: 10 }} tickFormatter={(v) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v} domain={['auto', 'auto']} />
                                                            <YAxis yAxisId="right" orientation="right" tick={{ fill: '#9ca3af', fontSize: 10 }} tickFormatter={(v) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v} domain={[(dataMin: number) => Math.floor(dataMin * 0.8), (dataMax: number) => Math.ceil(dataMax * 1.2)]} />
                                                            <Bar yAxisId="left" dataKey="impressions" fill="#64748b" radius={[2, 2, 0, 0]} />
                                                            <Line yAxisId="right" type="monotone" dataKey="clicks" stroke="#fbbf24" strokeWidth={2} dot={false} />
                                                        </ComposedChart>
                                                    </ResponsiveContainer>
                                                </div>
                                            )}

                                            {/* Chart 9: Impressions with Cumulative Conversions overlay */}
                                            {dataAvailability.metrics.impressions && dataAvailability.metrics.conversions && (
                                                <div className="h-[150px]" data-testid="chart-impressions-conversions">
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <span className="text-xs font-medium text-muted-foreground w-16">Impr</span>
                                                        <div className="flex gap-3 text-xs">
                                                            <span className="flex items-center gap-1"><span className="w-3 h-3 bg-slate-500 rounded-sm"></span> Impressions</span>
                                                            <span className="flex items-center gap-1"><span className="w-3 h-3 bg-purple-400 rounded-sm"></span> Conversions</span>
                                                        </div>
                                                    </div>
                                                    <ResponsiveContainer width="100%" height="100%">
                                                        <ComposedChart data={monthlyTrendData}>
                                                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
                                                            <XAxis dataKey="date" tick={{ fill: '#9ca3af', fontSize: 9 }} angle={-45} textAnchor="end" height={50} />
                                                            <YAxis yAxisId="left" tick={{ fill: '#9ca3af', fontSize: 10 }} tickFormatter={(v) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v} domain={['auto', 'auto']} />
                                                            <YAxis yAxisId="right" orientation="right" tick={{ fill: '#9ca3af', fontSize: 10 }} tickFormatter={(v) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v} domain={[(dataMin: number) => Math.floor(dataMin * 0.8), (dataMax: number) => Math.ceil(dataMax * 1.2)]} />
                                                            <Bar yAxisId="left" dataKey="impressions" fill="#64748b" radius={[2, 2, 0, 0]} />
                                                            <Line yAxisId="right" type="monotone" dataKey="conversions" stroke="#a78bfa" strokeWidth={2} dot={false} />
                                                        </ComposedChart>
                                                    </ResponsiveContainer>
                                                </div>
                                            )}
                                        </CardContent>
                                    </Card>
                                )}

                                {/* Channel Performance Table */}
                                <div className="mb-6">
                                    <PerformanceTable
                                        key={`channel-${selectedMonth}-${selectedPlatform}-${JSON.stringify(computedChannelPerformance?.slice(0, 1))}`}
                                        title={selectedMonth || selectedPlatform ? `Channel Performance (Filtered)` : "Channel Performance"}
                                        description={selectedMonth || selectedPlatform
                                            ? "Filtered by selected month/platform - Click selection again to show all"
                                            : "Click a channel to filter Monthly & Platform Performance"}
                                        data={computedChannelPerformance}
                                        type="channel"
                                        onChannelClick={(channel) => {
                                            setSelectedChannel(channel === selectedChannel ? null : channel);
                                            // Optional: clear other selections if you want exclusive focus
                                            // if (channel !== selectedChannel) { setSelectedMonth(null); setSelectedPlatform(null); }
                                        }}
                                        selectedChannel={selectedChannel}
                                        schema={schema || undefined}
                                    />
                                </div>

                                {/* Monthly & Platform Performance Tables */}
                                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                                    <PerformanceTable
                                        key={`monthly-${selectedPlatform}-${selectedChannel}-${JSON.stringify(dashboardStats.monthly_performance?.slice(0, 1))}`}
                                        title={selectedPlatform || selectedChannel ? `Monthly Performance (Filtered)` : "Monthly Performance"}
                                        description={selectedPlatform || selectedChannel
                                            ? "Filtered by selected criteria - Click again to clear"
                                            : "Click a month to filter Platform & Channel Performance"}
                                        data={computedMonthlyPerformance}
                                        type="month"
                                        onMonthClick={(month) => {
                                            setSelectedMonth(month === selectedMonth ? null : month);
                                            // Clear platform/channel selection when month is clicked for focused drill-down
                                            if (month !== selectedMonth) {
                                                setSelectedPlatform(null);
                                                setSelectedChannel(null);
                                            }
                                        }}
                                        selectedMonth={selectedMonth}
                                        schema={schema || undefined}
                                    />
                                    <PerformanceTable
                                        key={`platform-${selectedMonth}-${selectedChannel}-${JSON.stringify(dashboardStats.platform_performance?.slice(0, 1))}`}
                                        title={selectedMonth || selectedChannel ? `Platform Performance (Filtered)` : "Platform Performance"}
                                        description={selectedMonth || selectedChannel
                                            ? "Filtered by selected criteria - Click again to clear"
                                            : "Click a platform to filter Monthly & Channel Performance"}
                                        data={computedPlatformPerformance}
                                        type="platform"
                                        onPlatformClick={(platform) => {
                                            setSelectedPlatform(platform === selectedPlatform ? null : platform);
                                            // Clear month/channel selection when platform is clicked
                                            if (platform !== selectedPlatform) {
                                                setSelectedMonth(null);
                                                setSelectedChannel(null);
                                            }
                                        }}
                                        selectedPlatform={selectedPlatform}
                                        schema={schema || undefined}
                                    />
                                    {selectedMonth && dashboardStats.platform_performance.filter((p: any) => p.month === selectedMonth).length === 0 && (
                                        <div className="col-span-1 flex items-center justify-center p-8 text-center">
                                            <div className="text-muted-foreground">
                                                <p className="text-sm font-medium">No platform data for selected month</p>
                                                <p className="text-xs mt-1">Click the month again to show all data</p>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </motion.div>
                        </AnimatePresence>
                    </TabsContent>

                    {/* Channel Tab */}
                    <TabsContent value="channel" className="space-y-6">
                        <AnimatePresence mode="wait">
                            <motion.div
                                key="channel"
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -20 }}
                                className="space-y-6"
                            >
                                {/* Channel Performance Header */}
                                <div className="flex items-center justify-between">
                                    <div>
                                        <h2 className="text-2xl font-bold flex items-center gap-2">
                                            <BarChart3 className="h-6 w-6 text-primary" />
                                            Channel Performance
                                        </h2>
                                        <p className="text-muted-foreground">Deep dive into channel-level metrics and comparisons</p>
                                    </div>
                                </div>

                                {/* Channel KPI Cards */}
                                <div className="grid gap-4 grid-cols-2 md:grid-cols-4">
                                    {(() => {
                                        // Aggregate channel data
                                        const channels = computedChannelPerformance || channelData || [];
                                        const totalChannels = channels.length;
                                        const totalSpend = channels.reduce((sum: number, ch: any) => sum + (ch.spend || 0), 0);
                                        const totalConversions = channels.reduce((sum: number, ch: any) => sum + (ch.conversions || 0), 0);
                                        const avgCTR = channels.length > 0
                                            ? channels.reduce((sum: number, ch: any) => sum + (ch.ctr || 0), 0) / channels.length
                                            : 0;
                                        const avgCPA = totalConversions > 0 ? totalSpend / totalConversions : 0;

                                        // Find top performer
                                        const topChannel = channels.reduce((best: any, ch: any) =>
                                            (!best || (ch.conversions || 0) > (best.conversions || 0)) ? ch : best, null);

                                        return (
                                            <>
                                                <Card className="bg-gradient-to-br from-blue-500/10 to-blue-600/5 border-blue-500/20">
                                                    <CardHeader className="pb-2">
                                                        <CardDescription>Active Channels</CardDescription>
                                                        <CardTitle className="text-3xl font-bold text-blue-400">{totalChannels}</CardTitle>
                                                    </CardHeader>
                                                    <CardContent>
                                                        <p className="text-xs text-muted-foreground">Marketing channels tracked</p>
                                                    </CardContent>
                                                </Card>
                                                <Card className="bg-gradient-to-br from-green-500/10 to-green-600/5 border-green-500/20">
                                                    <CardHeader className="pb-2">
                                                        <CardDescription>Total Channel Spend</CardDescription>
                                                        <CardTitle className="text-3xl font-bold text-green-400">${formatNumber(totalSpend)}</CardTitle>
                                                    </CardHeader>
                                                    <CardContent>
                                                        <p className="text-xs text-muted-foreground">Across all channels</p>
                                                    </CardContent>
                                                </Card>
                                                <Card className="bg-gradient-to-br from-purple-500/10 to-purple-600/5 border-purple-500/20">
                                                    <CardHeader className="pb-2">
                                                        <CardDescription>Avg Channel CTR</CardDescription>
                                                        <CardTitle className="text-3xl font-bold text-purple-400">{avgCTR.toFixed(2)}%</CardTitle>
                                                    </CardHeader>
                                                    <CardContent>
                                                        <p className="text-xs text-muted-foreground">Average across channels</p>
                                                    </CardContent>
                                                </Card>
                                                <Card className="bg-gradient-to-br from-amber-500/10 to-amber-600/5 border-amber-500/20">
                                                    <CardHeader className="pb-2">
                                                        <CardDescription>Top Channel</CardDescription>
                                                        <CardTitle className="text-3xl font-bold text-amber-400">{topChannel?.channel || topChannel?.name || 'N/A'}</CardTitle>
                                                    </CardHeader>
                                                    <CardContent>
                                                        <p className="text-xs text-muted-foreground">
                                                            {topChannel ? `${formatNumber(topChannel.conversions || 0)} conversions` : 'By conversions'}
                                                        </p>
                                                    </CardContent>
                                                </Card>
                                            </>
                                        );
                                    })()}
                                </div>

                                {/* Channel Comparison Charts */}
                                <div className="space-y-6">
                                    {/* Top Chart: Spend vs ROAS */}
                                    <ComparisonChart
                                        title="Channel Spend vs ROAS"
                                        description="Compare spend efficiency against Return on Ad Spend"
                                        data={computedChannelPerformance || channelData || []}
                                        xKey="channel"
                                        yLeftKey="spend"
                                        yRightKey="roas"
                                        yLeftName="Spend ($)"
                                        yRightName="ROAS (x)"
                                        yLeftFormatter={(v) => `$${v.toLocaleString()}`}
                                        yRightFormatter={(v) => `${v.toFixed(2)}x`}
                                        yLeftColor="#6366f1"
                                        yRightColor="#facc15"
                                    />

                                    {/* Grid of Other Charts */}
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                        <ComparisonChart
                                            title="Spend vs Conversions"
                                            description="Correlation between spend and total conversions"
                                            data={computedChannelPerformance || channelData || []}
                                            xKey="channel"
                                            yLeftKey="spend"
                                            yRightKey="conversions"
                                            yLeftName="Spend ($)"
                                            yRightName="Conversions"
                                            yLeftFormatter={(v) => `$${v.toLocaleString()}`}
                                            yLeftColor="#3b82f6"
                                            yRightColor="#a78bfa"
                                        />
                                        <ComparisonChart
                                            title="Spend vs CTR"
                                            description="Spend impact on Click-Through Rate"
                                            data={computedChannelPerformance || channelData || []}
                                            xKey="channel"
                                            yLeftKey="spend"
                                            yRightKey="ctr"
                                            yLeftName="Spend ($)"
                                            yRightName="CTR (%)"
                                            yLeftFormatter={(v) => `$${v.toLocaleString()}`}
                                            yRightFormatter={(v) => `${v.toFixed(2)}%`}
                                            yLeftColor="#14b8a6"
                                            yRightColor="#fb923c"
                                        />
                                        <ComparisonChart
                                            title="Clicks vs CTR"
                                            description="Volume of clicks against click-through rate"
                                            data={computedChannelPerformance || channelData || []}
                                            xKey="channel"
                                            yLeftKey="clicks"
                                            yRightKey="ctr"
                                            yLeftName="Clicks"
                                            yRightName="CTR (%)"
                                            yRightFormatter={(v) => `${v.toFixed(2)}%`}
                                            yLeftColor="#f59e0b"
                                            yRightColor="#fb923c"
                                        />
                                        <ComparisonChart
                                            title="Clicks vs CPC"
                                            description="Clicks volume against Cost Per Click"
                                            data={computedChannelPerformance || channelData || []}
                                            xKey="channel"
                                            yLeftKey="clicks"
                                            yRightKey="cpc"
                                            yLeftName="Clicks"
                                            yRightName="CPC ($)"
                                            yRightFormatter={(v) => `$${v.toFixed(2)}`}
                                            yLeftColor="#f59e0b"
                                            yRightColor="#6366f1"
                                        />
                                        <ComparisonChart
                                            title="Clicks vs Conversions"
                                            description="Conversion rate from clicks"
                                            data={computedChannelPerformance || channelData || []}
                                            xKey="channel"
                                            yLeftKey="clicks"
                                            yRightKey="conversions"
                                            yLeftName="Clicks"
                                            yRightName="Conversions"
                                            yLeftColor="#f59e0b"
                                            yRightColor="#a78bfa"
                                        />
                                        <ComparisonChart
                                            title="Impressions vs Clicks"
                                            description="Funnel drop-off from impressions to clicks"
                                            data={computedChannelPerformance || channelData || []}
                                            xKey="channel"
                                            yLeftKey="impressions"
                                            yRightKey="clicks"
                                            yLeftName="Impressions"
                                            yRightName="Clicks"
                                            yLeftColor="#06b6d4"
                                            yRightColor="#fbbf24"
                                        />
                                        <ComparisonChart
                                            title="Impressions vs CPM"
                                            description="Impressions volume against Cost Per Mille"
                                            data={computedChannelPerformance || channelData || []}
                                            xKey="channel"
                                            yLeftKey="impressions"
                                            yRightKey="cpm"
                                            yLeftName="Impressions"
                                            yRightName="CPM ($)"
                                            yRightFormatter={(v) => `$${v.toFixed(2)}`}
                                            yLeftColor="#06b6d4"
                                            yRightColor="#d946ef"
                                        />
                                        <ComparisonChart
                                            title="Efficiency: CTR vs CPA"
                                            description="Engagement rate against Cost Per Acquisition"
                                            data={computedChannelPerformance || channelData || []}
                                            xKey="channel"
                                            yLeftKey="ctr"
                                            yRightKey="cpa"
                                            yLeftName="CTR (%)"
                                            yRightName="CPA ($)"
                                            yLeftFormatter={(v) => `${v.toFixed(2)}%`}
                                            yRightFormatter={(v) => `$${v.toFixed(2)}`}
                                            yLeftColor="#fb923c"
                                            yRightColor="#ec4899"
                                        />
                                    </div>
                                </div>

                                {/* Detailed Channel Performance Table */}
                                <PerformanceTable
                                    key={`channel-detailed-${selectedPlatform}-${JSON.stringify(computedChannelPerformance?.slice(0, 1))}`}
                                    title={selectedPlatform ? `Channel Performance (${selectedPlatform})` : "Channel Performance Details"}
                                    description={selectedPlatform
                                        ? "Filtered by selected platform - Click platform again to clear"
                                        : "Complete channel metrics - Click a row to filter Platform table"}
                                    data={computedChannelPerformance || channelData || []}
                                    type="channel"
                                    onChannelClick={(channel) => {
                                        setSelectedChannel(channel === selectedChannel ? null : channel);
                                    }}
                                    selectedChannel={selectedChannel}
                                    schema={schema || undefined}
                                />

                                {/* Linked Platform Performance Table */}
                                <PerformanceTable
                                    key={`platform-from-channel-${selectedChannel}-${JSON.stringify(computedPlatformPerformance?.slice(0, 1))}`}
                                    title={selectedChannel ? `Platform Performance (${selectedChannel} Channel)` : "Platform Performance"}
                                    description={selectedChannel
                                        ? "Filtered by selected channel - Click channel again to clear"
                                        : "Click a platform to filter Channel Performance above"}
                                    data={computedPlatformPerformance || platformData || []}
                                    type="platform"
                                    onPlatformClick={(platform) => {
                                        setSelectedPlatform(platform === selectedPlatform ? null : platform);
                                    }}
                                    selectedPlatform={selectedPlatform}
                                    schema={schema || undefined}
                                />
                            </motion.div>
                        </AnimatePresence>
                    </TabsContent>

                    {/* Platform Tab */}
                    <TabsContent value="platform" className="space-y-6">
                        <AnimatePresence mode="wait">
                            <motion.div
                                key="platform"
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -20 }}
                                className="space-y-6"
                            >
                                {/* Platform Performance Header */}
                                <div className="flex items-center justify-between">
                                    <div>
                                        <h2 className="text-2xl font-bold flex items-center gap-2">
                                            <Layers className="h-6 w-6 text-primary" />
                                            Platform Performance
                                        </h2>
                                        <p className="text-muted-foreground">Deep dive into platform-level metrics and comparisons</p>
                                    </div>
                                </div>

                                {/* Platform KPI Cards */}
                                <div className="grid gap-4 grid-cols-2 md:grid-cols-4">
                                    {(() => {
                                        // Aggregate platform data
                                        const platforms = computedPlatformPerformance || platformData || [];
                                        const totalPlatforms = platforms.length;
                                        const totalSpend = platforms.reduce((sum: number, p: any) => sum + (p.spend || 0), 0);
                                        const totalConversions = platforms.reduce((sum: number, p: any) => sum + (p.conversions || 0), 0);
                                        const avgCTR = platforms.length > 0
                                            ? platforms.reduce((sum: number, p: any) => sum + (p.ctr || 0), 0) / platforms.length
                                            : 0;

                                        // Find top performer
                                        const topPlatform = platforms.reduce((best: any, p: any) =>
                                            (!best || (p.conversions || 0) > (best.conversions || 0)) ? p : best, null);

                                        return (
                                            <>
                                                <Card className="bg-gradient-to-br from-cyan-500/10 to-cyan-600/5 border-cyan-500/20">
                                                    <CardHeader className="pb-2">
                                                        <CardDescription>Active Platforms</CardDescription>
                                                        <CardTitle className="text-3xl font-bold text-cyan-400">{totalPlatforms}</CardTitle>
                                                    </CardHeader>
                                                    <CardContent>
                                                        <p className="text-xs text-muted-foreground">Advertising platforms tracked</p>
                                                    </CardContent>
                                                </Card>
                                                <Card className="bg-gradient-to-br from-emerald-500/10 to-emerald-600/5 border-emerald-500/20">
                                                    <CardHeader className="pb-2">
                                                        <CardDescription>Total Platform Spend</CardDescription>
                                                        <CardTitle className="text-3xl font-bold text-emerald-400">${formatNumber(totalSpend)}</CardTitle>
                                                    </CardHeader>
                                                    <CardContent>
                                                        <p className="text-xs text-muted-foreground">Across all platforms</p>
                                                    </CardContent>
                                                </Card>
                                                <Card className="bg-gradient-to-br from-violet-500/10 to-violet-600/5 border-violet-500/20">
                                                    <CardHeader className="pb-2">
                                                        <CardDescription>Avg Platform CTR</CardDescription>
                                                        <CardTitle className="text-3xl font-bold text-violet-400">{avgCTR.toFixed(2)}%</CardTitle>
                                                    </CardHeader>
                                                    <CardContent>
                                                        <p className="text-xs text-muted-foreground">Average across platforms</p>
                                                    </CardContent>
                                                </Card>
                                                <Card className="bg-gradient-to-br from-orange-500/10 to-orange-600/5 border-orange-500/20">
                                                    <CardHeader className="pb-2">
                                                        <CardDescription>Top Platform</CardDescription>
                                                        <CardTitle className="text-3xl font-bold text-orange-400">{topPlatform?.platform || topPlatform?.name || 'N/A'}</CardTitle>
                                                    </CardHeader>
                                                    <CardContent>
                                                        <p className="text-xs text-muted-foreground">
                                                            {topPlatform ? `${formatNumber(topPlatform.conversions || 0)} conversions` : 'By conversions'}
                                                        </p>
                                                    </CardContent>
                                                </Card>
                                            </>
                                        );
                                    })()}
                                </div>

                                {/* Platform Comparison Charts */}
                                <div className="space-y-6">
                                    {/* Top Chart: Spend vs ROAS */}
                                    <ComparisonChart
                                        title="Platform Spend vs ROAS"
                                        description="Compare spend efficiency against Return on Ad Spend"
                                        data={computedPlatformPerformance || platformData || []}
                                        xKey="platform"
                                        yLeftKey="spend"
                                        yRightKey="roas"
                                        yLeftName="Spend ($)"
                                        yRightName="ROAS (x)"
                                        yLeftFormatter={(v) => `$${v.toLocaleString()}`}
                                        yRightFormatter={(v) => `${v.toFixed(2)}x`}
                                        yLeftColor="#6366f1"
                                        yRightColor="#facc15"
                                        limit={15}
                                    />

                                    {/* Grid of Other Charts */}
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                        <ComparisonChart
                                            title="Spend vs Conversions"
                                            description="Correlation between spend and total conversions"
                                            data={computedPlatformPerformance || platformData || []}
                                            xKey="platform"
                                            yLeftKey="spend"
                                            yRightKey="conversions"
                                            yLeftName="Spend ($)"
                                            yRightName="Conversions"
                                            yLeftFormatter={(v) => `$${v.toLocaleString()}`}
                                            yLeftColor="#3b82f6"
                                            yRightColor="#a78bfa"
                                        />
                                        <ComparisonChart
                                            title="Spend vs CTR"
                                            description="Spend impact on Click-Through Rate"
                                            data={computedPlatformPerformance || platformData || []}
                                            xKey="platform"
                                            yLeftKey="spend"
                                            yRightKey="ctr"
                                            yLeftName="Spend ($)"
                                            yRightName="CTR (%)"
                                            yLeftFormatter={(v) => `$${v.toLocaleString()}`}
                                            yRightFormatter={(v) => `${v.toFixed(2)}%`}
                                            yLeftColor="#14b8a6"
                                            yRightColor="#fb923c"
                                        />
                                        <ComparisonChart
                                            title="Clicks vs CTR"
                                            description="Volume of clicks against click-through rate"
                                            data={computedPlatformPerformance || platformData || []}
                                            xKey="platform"
                                            yLeftKey="clicks"
                                            yRightKey="ctr"
                                            yLeftName="Clicks"
                                            yRightName="CTR (%)"
                                            yRightFormatter={(v) => `${v.toFixed(2)}%`}
                                            yLeftColor="#f59e0b"
                                            yRightColor="#fb923c"
                                        />
                                        <ComparisonChart
                                            title="Clicks vs CPC"
                                            description="Clicks volume against Cost Per Click"
                                            data={computedPlatformPerformance || platformData || []}
                                            xKey="platform"
                                            yLeftKey="clicks"
                                            yRightKey="cpc"
                                            yLeftName="Clicks"
                                            yRightName="CPC ($)"
                                            yRightFormatter={(v) => `$${v.toFixed(2)}`}
                                            yLeftColor="#f59e0b"
                                            yRightColor="#6366f1"
                                        />
                                        <ComparisonChart
                                            title="Clicks vs Conversions"
                                            description="Conversion rate from clicks"
                                            data={computedPlatformPerformance || platformData || []}
                                            xKey="platform"
                                            yLeftKey="clicks"
                                            yRightKey="conversions"
                                            yLeftName="Clicks"
                                            yRightName="Conversions"
                                            yLeftColor="#f59e0b"
                                            yRightColor="#a78bfa"
                                        />
                                        <ComparisonChart
                                            title="Impressions vs Clicks"
                                            description="Funnel drop-off from impressions to clicks"
                                            data={computedPlatformPerformance || platformData || []}
                                            xKey="platform"
                                            yLeftKey="impressions"
                                            yRightKey="clicks"
                                            yLeftName="Impressions"
                                            yRightName="Clicks"
                                            yLeftColor="#06b6d4"
                                            yRightColor="#fbbf24"
                                        />
                                        <ComparisonChart
                                            title="Impressions vs CPM"
                                            description="Impressions volume against Cost Per Mille"
                                            data={computedPlatformPerformance || platformData || []}
                                            xKey="platform"
                                            yLeftKey="impressions"
                                            yRightKey="cpm"
                                            yLeftName="Impressions"
                                            yRightName="CPM ($)"
                                            yRightFormatter={(v) => `$${v.toFixed(2)}`}
                                            yLeftColor="#06b6d4"
                                            yRightColor="#d946ef"
                                        />
                                        <ComparisonChart
                                            title="Efficiency: CTR vs CPA"
                                            description="Engagement rate against Cost Per Acquisition"
                                            data={computedPlatformPerformance || platformData || []}
                                            xKey="platform"
                                            yLeftKey="ctr"
                                            yRightKey="cpa"
                                            yLeftName="CTR (%)"
                                            yRightName="CPA ($)"
                                            yLeftFormatter={(v) => `${v.toFixed(2)}%`}
                                            yRightFormatter={(v) => `$${v.toFixed(2)}`}
                                            yLeftColor="#fb923c"
                                            yRightColor="#ec4899"
                                        />
                                    </div>
                                </div>

                                {/* Platform Performance Table */}
                                <PerformanceTable
                                    key={`platform-detailed-${selectedChannel}-${JSON.stringify(computedPlatformPerformance?.slice(0, 1))}`}
                                    title={selectedChannel ? `Platform Performance (${selectedChannel} Channel)` : "Platform Performance Details"}
                                    description={selectedChannel
                                        ? "Filtered by selected channel - Click channel again to clear"
                                        : "Complete platform metrics - Click a row to filter Channel table"}
                                    data={computedPlatformPerformance || platformData || []}
                                    type="platform"
                                    onPlatformClick={(platform) => {
                                        setSelectedPlatform(platform === selectedPlatform ? null : platform);
                                    }}
                                    selectedPlatform={selectedPlatform}
                                    schema={schema || undefined}
                                />

                                {/* Linked Channel Performance Table REMOVED - Replaced by Breakdowns */}

                                <div className="space-y-6 mt-6">
                                    <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-widest pl-1">Detailed Breakdowns</h3>

                                    {/* 1. Audience Segment */}
                                    {audienceData && audienceData.length > 0 && (
                                        <PerformanceTable
                                            title="Audience Performances"
                                            description="Performance by audience segment"
                                            data={audienceData}
                                            type="audience"
                                            schema={schema || undefined}
                                        />
                                    )}

                                    {/* 2. Device - MOVED TO OTHER TAB */}
                                    {/* 3. Region */}
                                    {regionData && regionData.length > 0 && (
                                        <PerformanceTable
                                            title="Geographic Region Performance"
                                            description="Performance by region"
                                            data={regionData}
                                            type="region"
                                            schema={schema || undefined}
                                            onDimensionClick={(val) => setSelectedRegion(selectedRegion === val ? null : val)}
                                            selectedDimension={selectedRegion}
                                        />
                                    )}

                                    {/* 4. Age Group - MOVED TO OTHER TAB */}
                                    {/* 5. Ad Type - MOVED TO OTHER TAB */}
                                    {/* 6. Campaign Objective - MOVED TO OTHER TAB */}
                                    {/* 7. Targeting Type - MOVED TO OTHER TAB */}
                                </div>
                            </motion.div>
                        </AnimatePresence>
                    </TabsContent>

                    {/* Other Tab */}
                    <TabsContent value="other" className="space-y-6">
                        <AnimatePresence mode="wait">
                            <motion.div
                                key="other"
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -20 }}
                                className="space-y-6"
                            >
                                {/* 1. Ad Type (Top) */}
                                {adTypeData && adTypeData.length > 0 && (
                                    <PerformanceTable
                                        title="Ad Type Performance"
                                        description="Performance by creative format"
                                        data={adTypeData}
                                        type="ad_type"
                                        schema={schema || undefined}
                                        onDimensionClick={(val) => setSelectedAdType(selectedAdType === val ? null : val)}
                                        selectedDimension={selectedAdType}
                                    />
                                )}

                                {/* 2. Device */}
                                {deviceData && deviceData.length > 0 && (
                                    <PerformanceTable
                                        title="Device Performance"
                                        description="Performance by device type"
                                        data={deviceData}
                                        type="device"
                                        schema={schema || undefined}
                                        onDimensionClick={(val) => setSelectedDevice(selectedDevice === val ? null : val)}
                                        selectedDimension={selectedDevice}
                                    />
                                )}

                                {/* 3. Age Group */}
                                {ageData && ageData.length > 0 && (
                                    <PerformanceTable
                                        title="Age Group Performance"
                                        description="Performance by demographic age group"
                                        data={ageData}
                                        type="age"
                                        schema={schema || undefined}
                                        onDimensionClick={(val) => setSelectedAge(selectedAge === val ? null : val)}
                                        selectedDimension={selectedAge}
                                    />
                                )}

                                {/* 4. Campaign Objective */}
                                {objectiveData && objectiveData.length > 0 && (
                                    <PerformanceTable
                                        title="Campaign Objective Performance"
                                        description="Performance by optimization goal"
                                        data={objectiveData}
                                        type="objective"
                                        schema={schema || undefined}
                                        onDimensionClick={(val) => setSelectedObjective(selectedObjective === val ? null : val)}
                                        selectedDimension={selectedObjective}
                                    />
                                )}

                                {/* 5. Targeting Type */}
                                {targetingData && targetingData.length > 0 && (
                                    <PerformanceTable
                                        title="Targeting Type Performance"
                                        description="Performance by targeting strategy"
                                        data={targetingData}
                                        type="targeting"
                                        schema={schema || undefined}
                                        onDimensionClick={(val) => setSelectedTargeting(selectedTargeting === val ? null : val)}
                                        selectedDimension={selectedTargeting}
                                    />
                                )}
                            </motion.div>
                        </AnimatePresence>
                    </TabsContent>

                    {/* Funnel Tab */}
                    <TabsContent value="funnel" className="space-y-6">
                        <AnimatePresence mode="wait">
                            <motion.div
                                key="funnel"
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -20 }}
                                className="space-y-6"
                            >
                                {/* Funnel Performance Table */}
                                <PerformanceTable
                                    key={`funnel-${JSON.stringify(funnelStageData?.slice(0, 1))}`}
                                    title="Funnel Performance"
                                    description="Click a funnel stage to filter Channel Performance"
                                    data={funnelStageData}
                                    type="funnel"
                                    onFunnelStageClick={(stage) => setSelectedFunnelStage(stage === selectedFunnelStage ? null : stage)}
                                    selectedFunnelStage={selectedFunnelStage}
                                    schema={schema || undefined}
                                />

                                {/* Ad Type Performance Table (Linkable) */}
                                {adTypeData && adTypeData.length > 0 && (
                                    <PerformanceTable
                                        title="Ad Type Performance"
                                        description="Performance by creative format"
                                        data={adTypeData}
                                        type="ad_type"
                                        schema={schema || undefined}
                                        onDimensionClick={(val) => setSelectedAdType(selectedAdType === val ? null : val)}
                                        selectedDimension={selectedAdType}
                                    />
                                )}

                                {/* Channel Performance Table */}
                                <PerformanceTable
                                    key={`channel-${selectedFunnelStage}-${JSON.stringify(filteredChannelData?.slice(0, 1))}`}
                                    title={selectedFunnelStage ? `Channel Performance (${selectedFunnelStage} Funnel)` : "Channel Performance"}
                                    description="Performance breakdown across marketing channels"
                                    data={filteredChannelData}
                                    type="channel"
                                    schema={schema || undefined}
                                />

                                {/* Performance Funnel - Visual Funnel */}
                                <Card>
                                    <CardHeader>
                                        <CardTitle className="flex items-center gap-2">
                                            <Filter className="h-5 w-5" />
                                            Performance Funnel
                                        </CardTitle>
                                        <CardDescription>Conversion flow from impressions to conversions</CardDescription>
                                    </CardHeader>
                                    <CardContent className="h-[400px]">
                                        {kpis && (kpis.impressions > 0 || kpis.clicks > 0 || kpis.conversions > 0) ? (
                                            <div className="flex flex-col items-center justify-center h-full space-y-4">
                                                {(() => {
                                                    const ctr = kpis.impressions > 0 ? (kpis.clicks / kpis.impressions * 100).toFixed(1) : '0';
                                                    const conversionRate = kpis.clicks > 0 ? (kpis.conversions / kpis.clicks * 100).toFixed(1) : '0';

                                                    const formatNumber = (num: number) => {
                                                        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
                                                        if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
                                                        return num.toString();
                                                    };

                                                    return (
                                                        <>
                                                            {/* Impressions */}
                                                            <div className="relative w-full max-w-md">
                                                                <div className="bg-gradient-to-r from-indigo-500 to-indigo-600 text-white rounded-lg p-4 shadow-lg flex flex-col items-center justify-center gap-1" style={{ clipPath: 'polygon(5% 0%, 95% 0%, 90% 100%, 10% 100%)' }}>
                                                                    <div className="text-3xl font-bold text-center">{formatNumber(kpis.impressions)}</div>
                                                                    <div className="text-xs font-semibold text-indigo-100 uppercase tracking-wide">Impressions</div>
                                                                </div>
                                                            </div>

                                                            {/* Arrow & CTR */}
                                                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                                                <div className="h-8 w-0.5 bg-gradient-to-b from-indigo-500 to-purple-500"></div>
                                                                <span className="font-medium">CTR: {ctr}%</span>
                                                            </div>

                                                            {/* Clicks */}
                                                            <div className="relative w-full max-w-sm">
                                                                <div className="bg-gradient-to-r from-purple-500 to-purple-600 text-white rounded-lg p-4 shadow-lg flex flex-col items-center justify-center gap-1" style={{ clipPath: 'polygon(7% 0%, 93% 0%, 88% 100%, 12% 100%)' }}>
                                                                    <div className="text-3xl font-bold text-center">{formatNumber(kpis.clicks)}</div>
                                                                    <div className="text-xs font-semibold text-purple-100 uppercase tracking-wide">Clicks</div>
                                                                </div>
                                                            </div>

                                                            {/* Arrow & Conversion Rate */}
                                                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                                                <div className="h-8 w-0.5 bg-gradient-to-b from-purple-500 to-green-500"></div>
                                                                <span className="font-medium">Conv Rate: {conversionRate}%</span>
                                                            </div>

                                                            {/* Conversions */}
                                                            <div className="relative w-full max-w-xs">
                                                                <div className="bg-gradient-to-r from-green-500 to-green-600 text-white rounded-lg p-4 shadow-lg flex flex-col items-center justify-center gap-1" style={{ clipPath: 'polygon(10% 0%, 90% 0%, 85% 100%, 15% 100%)' }}>
                                                                    <div className="text-3xl font-bold text-center">{formatNumber(kpis.conversions)}</div>
                                                                    <div className="text-xs font-semibold text-green-100 uppercase tracking-wide">Conversions</div>
                                                                </div>
                                                            </div>
                                                        </>
                                                    );
                                                })()}
                                            </div >
                                        ) : (
                                            <div className="flex items-center justify-center h-full text-muted-foreground">
                                                No funnel data available
                                            </div>
                                        )}
                                    </CardContent>
                                </Card>
                            </motion.div>
                        </AnimatePresence>
                    </TabsContent>





                    {/* Performance Tab - Comparison View */}
                    <TabsContent value="performance" className="space-y-6">
                        <AnimatePresence mode="wait">
                            <motion.div
                                key="performance"
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -20 }}
                                className="space-y-6"
                            >
                                {/* Comparison Controls */}
                                <Card>
                                    <CardContent className="py-4">
                                        <div className="space-y-4">
                                            {/* Comparison Mode Selector */}
                                            <div className="space-y-1">
                                                <Label className="text-xs font-semibold">Comparison Mode</Label>
                                                <div className="flex gap-2">
                                                    <Button
                                                        variant={comparisonMode === 'auto' ? 'default' : 'outline'}
                                                        size="sm"
                                                        onClick={() => setComparisonMode('auto')}
                                                        className="flex-1"
                                                    >
                                                        Auto
                                                    </Button>
                                                    <Button
                                                        variant={comparisonMode === 'preset' ? 'default' : 'outline'}
                                                        size="sm"
                                                        onClick={() => setComparisonMode('preset')}
                                                        className="flex-1"
                                                    >
                                                        Presets
                                                    </Button>
                                                    <Button
                                                        variant={comparisonMode === 'custom' ? 'default' : 'outline'}
                                                        size="sm"
                                                        onClick={() => setComparisonMode('custom')}
                                                        className="flex-1"
                                                    >
                                                        Custom
                                                    </Button>
                                                </div>
                                            </div>

                                            {/* Preset Selector */}
                                            {kpiComparisonMode === 'preset' && (
                                                <div className="space-y-1">
                                                    <Label className="text-xs">Quick Compare</Label>
                                                    <Select value={kpiPreset} onValueChange={setKpiPreset}>
                                                        <SelectTrigger>
                                                            <SelectValue />
                                                        </SelectTrigger>
                                                        <SelectContent>
                                                            <SelectItem value="last_7_vs_prev_7">Last 7 days vs Previous 7 days</SelectItem>
                                                            <SelectItem value="last_30_vs_prev_30">Last 30 days vs Previous 30 days</SelectItem>
                                                            <SelectItem value="last_2_months_vs_prev_2_months">Last 2 months vs Previous 2 months</SelectItem>
                                                            <SelectItem value="last_3_months_vs_prev_3_months">Last 3 months vs Previous 3 months</SelectItem>
                                                        </SelectContent>
                                                    </Select>
                                                </div>
                                            )}

                                            {/* Date Comparison Display Box */}
                                            <div className="rounded-lg border border-border bg-muted/30 p-3 space-y-2">
                                                <div className="text-xs font-medium text-muted-foreground">Comparing Periods</div>
                                                <div className="space-y-1.5">
                                                    <div className="flex items-center gap-2">
                                                        <div className="h-2 w-2 rounded-full bg-cyan-500"></div>
                                                        <div className="text-xs">
                                                            <span className="font-medium">Current: </span>
                                                            <span className="text-muted-foreground">{comparisonDateRanges.periodA}</span>
                                                        </div>
                                                    </div>
                                                    <div className="flex items-center gap-2">
                                                        <div className="h-2 w-2 rounded-full bg-orange-500"></div>
                                                        <div className="text-xs">
                                                            <span className="font-medium">Previous: </span>
                                                            <span className="text-muted-foreground">{comparisonDateRanges.periodB}</span>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>

                                            {/* Dimension and Metric Selectors */}
                                            <div className="flex flex-wrap gap-4 items-end">
                                                <div className="space-y-1 min-w-[150px]">
                                                    <Label className="text-xs">Compare By (X-Axis)</Label>
                                                    <Select value={comparisonDimension} onValueChange={setComparisonDimension}>
                                                        <SelectTrigger><SelectValue /></SelectTrigger>
                                                        <SelectContent>
                                                            <SelectItem value="platform">Platform</SelectItem>
                                                            <SelectItem value="channel">Channel</SelectItem>
                                                            <SelectItem value="funnel_stage">Funnel Stage</SelectItem>
                                                        </SelectContent>
                                                    </Select>
                                                </div>
                                                <div className="space-y-1 min-w-[150px]">
                                                    <Label className="text-xs">Metric (Y-Axis)</Label>
                                                    <Select value={comparisonMetric} onValueChange={setComparisonMetric}>
                                                        <SelectTrigger><SelectValue /></SelectTrigger>
                                                        <SelectContent>
                                                            <SelectItem value="spend">Spend ($)</SelectItem>
                                                            <SelectItem value="impressions">Impressions</SelectItem>
                                                            <SelectItem value="clicks">Clicks</SelectItem>
                                                            <SelectItem value="conversions">Conversions</SelectItem>
                                                            <SelectItem value="ctr">CTR (%)</SelectItem>
                                                            <SelectItem value="cpc">CPC ($)</SelectItem>
                                                            <SelectItem value="cpa">CPA ($)</SelectItem>
                                                            {dataAvailability.metrics.roas && <SelectItem value="roas">ROAS</SelectItem>}
                                                        </SelectContent>
                                                    </Select>
                                                </div>
                                                {/* Dual Axis Controls */}
                                                <div className="flex items-center space-x-2 pt-5">
                                                    <input
                                                        type="checkbox"
                                                        id="dualAxis"
                                                        checked={isDualAxis}
                                                        onChange={(e) => {
                                                            setIsDualAxis(e.target.checked);
                                                            if (!e.target.checked) {
                                                                setComparisonMetric2("");
                                                                setComparisonData2([]);
                                                            }
                                                        }}
                                                        className="h-4 w-4 rounded border-gray-300"
                                                    />
                                                    <Label htmlFor="dualAxis" className="text-xs cursor-pointer">Dual Axis</Label>
                                                </div>
                                                {isDualAxis && (
                                                    <div className="space-y-1 min-w-[150px]">
                                                        <Label className="text-xs">Secondary Y-Axis</Label>
                                                        <Select value={comparisonMetric2} onValueChange={setComparisonMetric2}>
                                                            <SelectTrigger><SelectValue placeholder="Select metric" /></SelectTrigger>
                                                            <SelectContent>
                                                                <SelectItem value="spend">Spend ($)</SelectItem>
                                                                <SelectItem value="impressions">Impressions</SelectItem>
                                                                <SelectItem value="clicks">Clicks</SelectItem>
                                                                <SelectItem value="conversions">Conversions</SelectItem>
                                                                <SelectItem value="ctr">CTR (%)</SelectItem>
                                                                <SelectItem value="cpc">CPC ($)</SelectItem>
                                                                <SelectItem value="cpa">CPA ($)</SelectItem>
                                                                {dataAvailability.metrics.roas && <SelectItem value="roas">ROAS</SelectItem>}
                                                            </SelectContent>
                                                        </Select>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </CardContent>
                                </Card>

                                {/* KPI Cards with Comparison Period Selector */}
                                {kpiMetrics && (
                                    <div className="space-y-4">
                                        {/* Period Comparison Controls */}
                                        <Card className="bg-muted/30">
                                            <CardContent className="py-4">
                                                <div className="flex flex-wrap items-start gap-4">
                                                    {/* Mode Selector */}
                                                    <div className="space-y-1">
                                                        <Label className="text-xs font-semibold">Comparison Mode</Label>
                                                        <div className="flex gap-1">
                                                            <Button
                                                                variant={kpiComparisonMode === 'auto' ? 'default' : 'outline'}
                                                                size="sm"
                                                                onClick={() => setKpiComparisonMode('auto')}
                                                                className="h-8 px-3"
                                                            >
                                                                Auto
                                                            </Button>
                                                            <Button
                                                                variant={kpiComparisonMode === 'preset' ? 'default' : 'outline'}
                                                                size="sm"
                                                                onClick={() => setKpiComparisonMode('preset')}
                                                                className="h-8 px-3"
                                                            >
                                                                Presets
                                                            </Button>
                                                            <Button
                                                                variant={kpiComparisonMode === 'custom' ? 'default' : 'outline'}
                                                                size="sm"
                                                                onClick={() => setKpiComparisonMode('custom')}
                                                                className="h-8 px-3"
                                                            >
                                                                Custom
                                                            </Button>
                                                        </div>
                                                    </div>

                                                    {/* Auto Mode - Period Type Selector */}
                                                    {kpiComparisonMode === 'auto' && (
                                                        <div className="space-y-1">
                                                            <Label className="text-xs">Compare Period</Label>
                                                            <Select value={kpiComparisonPeriod} onValueChange={setKpiComparisonPeriod}>
                                                                <SelectTrigger className="w-[160px] h-8">
                                                                    <SelectValue />
                                                                </SelectTrigger>
                                                                <SelectContent>
                                                                    <SelectItem value="yoy">Year over Year</SelectItem>
                                                                    <SelectItem value="qoq">Quarter over Quarter</SelectItem>
                                                                    <SelectItem value="mom">Month over Month</SelectItem>
                                                                    <SelectItem value="wow">Week over Week</SelectItem>
                                                                </SelectContent>
                                                            </Select>
                                                        </div>
                                                    )}

                                                    {/* Preset Mode - Quick Presets */}
                                                    {kpiComparisonMode === 'preset' && (
                                                        <div className="space-y-1">
                                                            <Label className="text-xs">Quick Compare</Label>
                                                            <Select value={kpiPreset} onValueChange={setKpiPreset}>
                                                                <SelectTrigger className="w-[220px] h-8">
                                                                    <SelectValue />
                                                                </SelectTrigger>
                                                                <SelectContent>
                                                                    <SelectItem value="last_7_vs_prev_7">Last 7 days vs Previous 7 days</SelectItem>
                                                                    <SelectItem value="last_30_vs_prev_30">Last 30 days vs Previous 30 days</SelectItem>
                                                                    <SelectItem value="last_90_vs_prev_90">Last 90 days vs Previous 90 days</SelectItem>
                                                                    <SelectItem value="ytd_vs_prev_ytd">Year to Date vs Prior Year</SelectItem>
                                                                </SelectContent>
                                                            </Select>
                                                        </div>
                                                    )}

                                                    {/* Custom Mode - Date Range Pickers */}
                                                    {kpiComparisonMode === 'custom' && (
                                                        <>
                                                            <div className="space-y-1">
                                                                <Label className="text-xs">Period A (Current)</Label>
                                                                <DateRangePicker
                                                                    date={kpiPeriodA}
                                                                    onDateChange={setKpiPeriodA}
                                                                />
                                                            </div>
                                                            <div className="space-y-1">
                                                                <Label className="text-xs">Period B (Comparison)</Label>
                                                                <DateRangePicker
                                                                    date={kpiPeriodB}
                                                                    onDateChange={setKpiPeriodB}
                                                                />
                                                            </div>
                                                        </>
                                                    )}
                                                </div>
                                            </CardContent>
                                        </Card>

                                        {/* KPI Title */}
                                        <h3 className="text-lg font-semibold">Key Performance Indicators</h3>


                                        {/* KPI Card Groups */}
                                        <div className="grid gap-4 md:grid-cols-3">
                                            {/* SPEND & IMPRESSIONS Group */}
                                            <Card className="bg-gradient-to-r from-green-500/90 to-green-600/90 text-white border-0">
                                                <CardHeader className="pb-2 pt-3">
                                                    <CardTitle className="text-xs font-bold uppercase tracking-wider opacity-90">
                                                        Spend & Impressions
                                                    </CardTitle>
                                                </CardHeader>
                                                <CardContent className="pt-0">
                                                    <div className={`grid ${dataAvailability.metrics.roas ? 'grid-cols-4' : 'grid-cols-3'} gap-3`}>
                                                        <div>
                                                            <p className="text-[10px] uppercase opacity-70">Cost</p>
                                                            <p className="text-lg font-bold">${(kpiMetrics.spend.current / 1000000).toFixed(1)}M</p>
                                                            <p className={`text-[10px] flex items-center gap-0.5 ${kpiMetrics.spend.delta >= 0 ? 'text-green-200' : 'text-red-200'}`}>
                                                                {kpiMetrics.spend.delta >= 0 ? '↗' : '↘'}{Math.abs(kpiMetrics.spend.delta).toFixed(0)}%
                                                            </p>
                                                        </div>
                                                        <div>
                                                            <p className="text-[10px] uppercase opacity-70">CPM</p>
                                                            <p className="text-lg font-bold">${kpiMetrics.cpm.current.toFixed(2)}</p>
                                                            <p className={`text-[10px] flex items-center gap-0.5 ${kpiMetrics.cpm.delta >= 0 ? 'text-red-200' : 'text-green-200'}`}>
                                                                {kpiMetrics.cpm.delta >= 0 ? '↗' : '↘'}{Math.abs(kpiMetrics.cpm.delta).toFixed(0)}%
                                                            </p>
                                                        </div>
                                                        <div>
                                                            <p className="text-[10px] uppercase opacity-70">Impressions</p>
                                                            <p className="text-lg font-bold">{(kpiMetrics.impressions.current / 1000000).toFixed(1)}M</p>
                                                            <p className={`text-[10px] flex items-center gap-0.5 ${kpiMetrics.impressions.delta >= 0 ? 'text-green-200' : 'text-red-200'}`}>
                                                                {kpiMetrics.impressions.delta >= 0 ? '↗' : '↘'}{Math.abs(kpiMetrics.impressions.delta).toFixed(0)}%
                                                            </p>
                                                        </div>
                                                        <div>
                                                            <p className="text-[10px] uppercase opacity-70">Reach</p>
                                                            <p className="text-lg font-bold">{(kpiMetrics.reach.current / 1000000).toFixed(1)}M</p>
                                                            <p className={`text-[10px] flex items-center gap-0.5 ${kpiMetrics.reach.delta >= 0 ? 'text-green-200' : 'text-red-200'}`}>
                                                                {kpiMetrics.reach.delta >= 0 ? '↗' : '↘'}{Math.abs(kpiMetrics.reach.delta).toFixed(0)}%
                                                            </p>
                                                        </div>
                                                    </div>
                                                </CardContent>
                                            </Card>

                                            {/* CLICKS Group */}
                                            <Card className="bg-gradient-to-r from-amber-500/90 to-orange-500/90 text-white border-0">
                                                <CardHeader className="pb-2 pt-3">
                                                    <CardTitle className="text-xs font-bold uppercase tracking-wider opacity-90">
                                                        Clicks
                                                    </CardTitle>
                                                </CardHeader>
                                                <CardContent className="pt-0">
                                                    <div className="grid grid-cols-3 gap-3">
                                                        <div>
                                                            <p className="text-[10px] uppercase opacity-70">Clicks</p>
                                                            <p className="text-lg font-bold">{(kpiMetrics.clicks.current / 1000000).toFixed(1)}M</p>
                                                            <p className={`text-[10px] flex items-center gap-0.5 ${kpiMetrics.clicks.delta >= 0 ? 'text-green-200' : 'text-red-200'}`}>
                                                                {kpiMetrics.clicks.delta >= 0 ? '↗' : '↘'}{Math.abs(kpiMetrics.clicks.delta).toFixed(0)}%
                                                            </p>
                                                        </div>
                                                        <div>
                                                            <p className="text-[10px] uppercase opacity-70">CTR</p>
                                                            <p className="text-lg font-bold">{kpiMetrics.ctr.current.toFixed(2)}%</p>
                                                            <p className={`text-[10px] flex items-center gap-0.5 ${kpiMetrics.ctr.delta >= 0 ? 'text-green-200' : 'text-red-200'}`}>
                                                                {kpiMetrics.ctr.delta >= 0 ? '↗' : '↘'}{Math.abs(kpiMetrics.ctr.delta).toFixed(0)}%
                                                            </p>
                                                        </div>
                                                        <div>
                                                            <p className="text-[10px] uppercase opacity-70">CPC</p>
                                                            <p className="text-lg font-bold">${kpiMetrics.cpc.current.toFixed(2)}</p>
                                                            <p className={`text-[10px] flex items-center gap-0.5 ${kpiMetrics.cpc.delta >= 0 ? 'text-red-200' : 'text-green-200'}`}>
                                                                {kpiMetrics.cpc.delta >= 0 ? '↗' : '↘'}{Math.abs(kpiMetrics.cpc.delta).toFixed(0)}%
                                                            </p>
                                                        </div>
                                                    </div>
                                                </CardContent>
                                            </Card>

                                            {/* CONVERSIONS Group */}
                                            <Card className="bg-gradient-to-r from-blue-500/90 to-blue-600/90 text-white border-0">
                                                <CardHeader className="pb-2 pt-3">
                                                    <CardTitle className="text-xs font-bold uppercase tracking-wider opacity-90">
                                                        Conversions
                                                    </CardTitle>
                                                </CardHeader>
                                                <CardContent className="pt-0">
                                                    <div className={`grid ${dataAvailability.metrics.roas ? 'grid-cols-4' : 'grid-cols-3'} gap-3`}>
                                                        <div>
                                                            <p className="text-[10px] uppercase opacity-70">Conversions</p>
                                                            <p className="text-lg font-bold">{(kpiMetrics.conversions.current / 1000000).toFixed(1)}M</p>
                                                            <p className={`text-[10px] flex items-center gap-0.5 ${kpiMetrics.conversions.delta >= 0 ? 'text-green-200' : 'text-red-200'}`}>
                                                                {kpiMetrics.conversions.delta >= 0 ? '↗' : '↘'}{Math.abs(kpiMetrics.conversions.delta).toFixed(0)}%
                                                            </p>
                                                        </div>
                                                        <div>
                                                            <p className="text-[10px] uppercase opacity-70">Conv Rate</p>
                                                            <p className="text-lg font-bold">{kpiMetrics.convRate.current.toFixed(2)}%</p>
                                                            <p className={`text-[10px] flex items-center gap-0.5 ${kpiMetrics.convRate.delta >= 0 ? 'text-green-200' : 'text-red-200'}`}>
                                                                {kpiMetrics.convRate.delta >= 0 ? '↗' : '↘'}{Math.abs(kpiMetrics.convRate.delta).toFixed(0)}%
                                                            </p>
                                                        </div>
                                                        <div>
                                                            <p className="text-[10px] uppercase opacity-70">CPA</p>
                                                            <p className="text-lg font-bold">${kpiMetrics.cpa.current.toFixed(2)}</p>
                                                            <p className={`text-[10px] flex items-center gap-0.5 ${kpiMetrics.cpa.delta >= 0 ? 'text-red-200' : 'text-green-200'}`}>
                                                                {kpiMetrics.cpa.delta >= 0 ? '↗' : '↘'}{Math.abs(kpiMetrics.cpa.delta).toFixed(0)}%
                                                            </p>
                                                        </div>
                                                        {dataAvailability.metrics.roas && (
                                                            <div>
                                                                <p className="text-[10px] uppercase opacity-70">ROAS</p>
                                                                <p className="text-lg font-bold">{kpiMetrics.roas.current.toFixed(2)}x</p>
                                                                <p className={`text-[10px] flex items-center gap-0.5 ${kpiMetrics.roas.delta >= 0 ? 'text-green-200' : 'text-red-200'}`}>
                                                                    {kpiMetrics.roas.delta >= 0 ? '↗' : '↘'}{Math.abs(kpiMetrics.roas.delta).toFixed(0)}%
                                                                </p>
                                                            </div>
                                                        )}
                                                    </div>
                                                </CardContent>
                                            </Card>
                                        </div>
                                    </div>
                                )}


                                {/* Comparison Chart */}
                                <Card>
                                    <CardHeader>
                                        <CardTitle className="flex items-center justify-between">
                                            Comparison Chart {isDualAxis && `(Dual Axis)`}
                                            <div className="flex items-center gap-4 text-xs font-normal">
                                                <div className="flex items-center gap-1">
                                                    <div className="w-3 h-3 rounded-full" style={{ background: 'linear-gradient(135deg, #06b6d4, #0891b2)' }}></div>
                                                    Current ({comparisonMetric})
                                                </div>
                                                <div className="flex items-center gap-1">
                                                    <div className="w-3 h-3 rounded-full" style={{ background: 'linear-gradient(135deg, #f97316, #ea580c)' }}></div>
                                                    Previous ({comparisonMetric})
                                                </div>
                                                {isDualAxis && comparisonMetric2 && (
                                                    <div className="flex items-center gap-1">
                                                        <div className="w-3 h-3 rounded-full bg-amber-500"></div>
                                                        {comparisonMetric2} (Right Axis)
                                                    </div>
                                                )}
                                            </div>
                                        </CardTitle>
                                        <CardDescription>
                                            {isDualAxis && comparisonMetric2
                                                ? `${comparisonMetric} vs ${comparisonMetric2} across ${comparisonDimension}`
                                                : `Side-by-side view of ${comparisonMetric} across ${comparisonDimension}`
                                            }
                                        </CardDescription>
                                    </CardHeader>
                                    <CardContent>
                                        {loading ? (
                                            <div className="flex items-center justify-center h-[400px]">
                                                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                                            </div>
                                        ) : (
                                            <div className="h-[400px]">
                                                <ResponsiveContainer width="100%" height="100%">
                                                    <ComposedChart data={comparisonData}>
                                                        <defs>
                                                            <linearGradient id="currentGradient" x1="0" y1="0" x2="0" y2="1">
                                                                <stop offset="0%" stopColor="#06b6d4" />
                                                                <stop offset="100%" stopColor="#0891b2" />
                                                            </linearGradient>
                                                            <linearGradient id="previousGradient" x1="0" y1="0" x2="0" y2="1">
                                                                <stop offset="0%" stopColor="#f97316" />
                                                                <stop offset="100%" stopColor="#ea580c" />
                                                            </linearGradient>
                                                        </defs>
                                                        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                                                        <XAxis dataKey="dimension" className="text-xs" />
                                                        <YAxis yAxisId="left" className="text-xs" />
                                                        {isDualAxis && comparisonMetric2 && (
                                                            <YAxis yAxisId="right" orientation="right" className="text-xs" stroke="#f59e0b" />
                                                        )}
                                                        <Tooltip
                                                            contentStyle={{ backgroundColor: 'var(--background)', borderColor: 'var(--border)', borderRadius: '8px' }}
                                                        />
                                                        <Legend />
                                                        <Bar yAxisId="left" dataKey="current" name={`Current ${comparisonMetric}`} fill="url(#currentGradient)" radius={[4, 4, 0, 0]} />
                                                        <Bar yAxisId="left" dataKey="previous" name={`Previous ${comparisonMetric}`} fill="url(#previousGradient)" radius={[4, 4, 0, 0]} />
                                                        {isDualAxis && comparisonMetric2 && (
                                                            <Line
                                                                yAxisId="right"
                                                                type="monotone"
                                                                dataKey="secondary"
                                                                name={comparisonMetric2.toUpperCase()}
                                                                stroke="#f59e0b"
                                                                strokeWidth={3}
                                                                dot={{ fill: '#f59e0b', r: 5 }}
                                                            />
                                                        )}
                                                    </ComposedChart>
                                                </ResponsiveContainer>
                                            </div>
                                        )}
                                    </CardContent>
                                </Card>


                                {/* Channel Year-over-Year Comparison Table */}
                                <Card>
                                    <CardHeader>
                                        <div className="flex items-center justify-between">
                                            <div>
                                                <CardTitle className="flex items-center gap-2">
                                                    <TrendingUp className="h-5 w-5" />
                                                    Channel Year-over-Year Comparison
                                                </CardTitle>
                                                <CardDescription>
                                                    Comparing {channelCompYear1} vs {channelCompYear2} metrics by channel
                                                </CardDescription>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <Select value={String(channelCompYear1)} onValueChange={(v) => setChannelCompYear1(Number(v))}>
                                                    <SelectTrigger className="w-[100px]">
                                                        <SelectValue />
                                                    </SelectTrigger>
                                                    <SelectContent>
                                                        <SelectItem value="2025">2025</SelectItem>
                                                        <SelectItem value="2024">2024</SelectItem>
                                                    </SelectContent>
                                                </Select>
                                                <span className="text-muted-foreground">vs</span>
                                                <Select value={String(channelCompYear2)} onValueChange={(v) => setChannelCompYear2(Number(v))}>
                                                    <SelectTrigger className="w-[100px]">
                                                        <SelectValue />
                                                    </SelectTrigger>
                                                    <SelectContent>
                                                        <SelectItem value="2025">2025</SelectItem>
                                                        <SelectItem value="2024">2024</SelectItem>
                                                    </SelectContent>
                                                </Select>
                                            </div>
                                        </div>
                                    </CardHeader>
                                    <CardContent>
                                        {channelCompLoading ? (
                                            <div className="flex items-center justify-center h-[300px]">
                                                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                                            </div>
                                        ) : (
                                            <div className="rounded-md border overflow-x-auto">
                                                <table className="w-full text-sm">
                                                    <thead className="bg-muted/50 sticky top-0">
                                                        <tr className="border-b">
                                                            <th className="px-4 py-3 text-left font-medium sticky left-0 bg-muted/50">Channel</th>
                                                            <th className="px-3 py-3 text-right font-medium text-xs">Spend {channelCompYear1}</th>
                                                            <th className="px-3 py-3 text-right font-medium text-xs">Spend {channelCompYear2}</th>
                                                            <th className="px-3 py-3 text-right font-medium text-xs">% Change</th>
                                                            <th className="px-3 py-3 text-right font-medium text-xs">CTR {channelCompYear1}</th>
                                                            <th className="px-3 py-3 text-right font-medium text-xs">CTR {channelCompYear2}</th>
                                                            <th className="px-3 py-3 text-right font-medium text-xs">% Change</th>
                                                            <th className="px-3 py-3 text-right font-medium text-xs">Conv {channelCompYear1}</th>
                                                            <th className="px-3 py-3 text-right font-medium text-xs">Conv {channelCompYear2}</th>
                                                            <th className="px-3 py-3 text-right font-medium text-xs">% Change</th>
                                                            <th className="px-3 py-3 text-right font-medium text-xs">CPA {channelCompYear1}</th>
                                                            <th className="px-3 py-3 text-right font-medium text-xs">CPA {channelCompYear2}</th>
                                                            <th className="px-3 py-3 text-right font-medium text-xs">% Change</th>
                                                            {dataAvailability.metrics.roas && (
                                                                <>
                                                                    <th className="px-3 py-3 text-right font-medium text-xs">ROAS {channelCompYear1}</th>
                                                                    <th className="px-3 py-3 text-right font-medium text-xs">ROAS {channelCompYear2}</th>
                                                                    <th className="px-3 py-3 text-right font-medium text-xs">% Change</th>
                                                                </>
                                                            )}
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        {channelCompData.map((row, idx) => (
                                                            <tr key={idx} className="border-b hover:bg-muted/30 transition-colors">
                                                                <td
                                                                    className="px-4 py-3 font-medium sticky left-0 bg-background cursor-pointer hover:text-blue-500 transition-colors"
                                                                    onClick={() => {
                                                                        setSelectedChannel(row.channel);
                                                                        setActiveTab('overview');
                                                                        // Small timeout to allow tab switch before scroll
                                                                        setTimeout(() => {
                                                                            window.scrollTo({ top: 1000, behavior: 'smooth' });
                                                                        }, 100);
                                                                    }}
                                                                >
                                                                    <div className="flex items-center gap-1">
                                                                        {row.channel}
                                                                        <ArrowUpRight className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                                                                    </div>
                                                                </td>
                                                                {/* Spend */}
                                                                <td className="px-3 py-2 text-right">${(row.spend2025 / 1000).toFixed(1)}k</td>
                                                                <td className="px-3 py-2 text-right text-muted-foreground">${(row.spend2024 / 1000).toFixed(1)}k</td>
                                                                <td className={`px-3 py-2 text-right font-medium ${row.spendChange >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                                                                    {row.spendChange >= 0 ? '+' : ''}{row.spendChange.toFixed(1)}%
                                                                </td>
                                                                {/* CTR */}
                                                                <td className="px-3 py-2 text-right">{row.ctr2025.toFixed(2)}%</td>
                                                                <td className="px-3 py-2 text-right text-muted-foreground">{row.ctr2024.toFixed(2)}%</td>
                                                                <td className={`px-3 py-2 text-right font-medium ${row.ctrChange >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                                                                    {row.ctrChange >= 0 ? '+' : ''}{row.ctrChange.toFixed(1)}%
                                                                </td>
                                                                {/* Conversions */}
                                                                <td className="px-3 py-2 text-right">{row.conversions2025.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td>
                                                                <td className="px-3 py-2 text-right text-muted-foreground">{row.conversions2024.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td>
                                                                <td className={`px-3 py-2 text-right font-medium ${row.conversionsChange >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                                                                    {row.conversionsChange >= 0 ? '+' : ''}{row.conversionsChange.toFixed(1)}%
                                                                </td>
                                                                {/* CPA - lower is better, so green when negative */}
                                                                <td className="px-3 py-2 text-right">${row.cpa2025.toFixed(2)}</td>
                                                                <td className="px-3 py-2 text-right text-muted-foreground">${row.cpa2024.toFixed(2)}</td>
                                                                <td className={`px-3 py-2 text-right font-medium ${row.cpaChange >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                                                                    {row.cpaChange >= 0 ? '+' : ''}{row.cpaChange.toFixed(1)}%
                                                                </td>
                                                                {/* ROAS */}
                                                                {dataAvailability.metrics.roas && (
                                                                    <>
                                                                        <td className="px-3 py-2 text-right">{row.roas2025.toFixed(2)}x</td>
                                                                        <td className="px-3 py-2 text-right text-muted-foreground">{row.roas2024.toFixed(2)}x</td>
                                                                        <td className={`px-3 py-2 text-right font-medium ${row.roasChange >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                                                                            {row.roasChange >= 0 ? '+' : ''}{row.roasChange.toFixed(1)}%
                                                                        </td>
                                                                    </>
                                                                )}
                                                            </tr>
                                                        ))}
                                                        {channelCompData.length === 0 && !channelCompLoading && (
                                                            <tr>
                                                                <td colSpan={dataAvailability.metrics.roas ? 16 : 13} className="px-4 py-8 text-center text-muted-foreground">
                                                                    No channel comparison data available.
                                                                </td>
                                                            </tr>
                                                        )}
                                                    </tbody>
                                                </table>
                                            </div>
                                        )}
                                    </CardContent>
                                </Card>
                            </motion.div>
                        </AnimatePresence>
                    </TabsContent>

                </Tabs>

                {/* Drill-down Modal */}
                <DrillDownModal
                    isOpen={drillDownOpen}
                    onClose={() => setDrillDownOpen(false)}
                    dimension={drillDownData.dimension}
                    value={drillDownData.value}
                    data={drillDownData.data}
                />
            </div>
        </div>
    );
}

export default function AdsOverview() {
    return (
        <DashboardProvider>
            <AdsOverviewContent />
        </DashboardProvider>
    );
}
