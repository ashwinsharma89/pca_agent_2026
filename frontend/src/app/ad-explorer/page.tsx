"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

// Simple layout without auth
function SimpleLayout({ children }: { children: React.ReactNode }) {
    return (
        <div className="min-h-screen bg-[#0a0e1a] text-[#f1f5f9]">
            <header className="border-b border-[#334155] bg-[#0f172a]/80 backdrop-blur-xl sticky top-0 z-50">
                <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
                    <Link href="/ad-explorer" className="flex items-center gap-2 font-bold text-lg">
                        <span className="text-2xl">📊</span>
                        Ad Platform Data Explorer
                    </Link>
                    <div className="flex items-center gap-4 text-sm text-[#94a3b8]">
                        <span>Google Ads • Meta Ads</span>
                    </div>
                </div>
            </header>
            <main>{children}</main>
        </div>
    );
}

// Platform options
const PLATFORMS = [
    { id: "google_ads", name: "Google Ads", icon: "🔵" },
    { id: "meta_ads", name: "Meta Ads", icon: "🔷" },
    { id: "tiktok_ads", name: "TikTok Ads", icon: "🎵" },
    { id: "linkedin_ads", name: "LinkedIn Ads", icon: "💼" },
];

// Metadata for known columns (Label, Formatting, Grouping)
// This is used to enhance the display of columns returned by the API
const COLUMN_METADATA: Record<string, { label: string; group: string; format?: string }> = {
    // Campaign Level
    campaign_name: { label: "Campaign", group: "Campaign" },
    campaign_status: { label: "Status", group: "Campaign" },
    campaign_objective: { label: "Objective", group: "Campaign" },
    campaign_budget: { label: "Budget", group: "Campaign", format: "currency" },
    campaign_spend: { label: "Camp. Spend", group: "Campaign", format: "currency" },

    // Ad Group / Set Level
    ad_group_name: { label: "Ad Group", group: "Ad Group" },
    ad_group_status: { label: "AG Status", group: "Ad Group" },
    ad_group_type: { label: "AG Type", group: "Ad Group" },
    ad_set_name: { label: "Ad Set", group: "Ad Set" },
    ad_set_status: { label: "AS Status", group: "Ad Set" },
    ad_set_optimization: { label: "Optimization", group: "Ad Set" },

    // Ad Level
    ad_name: { label: "Ad", group: "Ad" },
    ad_status: { label: "Ad Status", group: "Ad" },
    ad_type: { label: "Ad Type", group: "Ad" },
    ad_format: { label: "Format", group: "Ad" },

    // Metrics (Always aggregated)
    ad_spend: { label: "Spend", group: "Metrics", format: "currency" },
    ad_impressions: { label: "Impressions", group: "Metrics", format: "number" },
    ad_clicks: { label: "Clicks", group: "Metrics", format: "number" },
    ad_conversions: { label: "Conversions", group: "Metrics", format: "number" },
    ad_ctr: { label: "CTR", group: "Metrics", format: "percent" },
    ad_cpc: { label: "CPC", group: "Metrics", format: "currency" },
    ad_cpa: { label: "CPA", group: "Metrics", format: "currency" },
};

const METRIC_KEYS = new Set([
    "ad_spend", "ad_impressions", "ad_clicks", "ad_conversions",
    "ad_ctr", "ad_cpc", "ad_cpa"
]);

// Format value based on type
function formatValue(value: any, format?: string): string {
    if (value === null || value === undefined) return "-";
    switch (format) {
        case "currency":
            return `$${Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        case "number":
            return Number(value).toLocaleString();
        case "percent":
            return `${Number(value).toFixed(2)}%`;
        default:
            return String(value);
    }
}

export default function AdExplorerPage() {
    const [platform, setPlatform] = useState("google_ads");
    const [startDate, setStartDate] = useState(new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]);
    const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0]);
    const [granularity, setGranularity] = useState<"Campaign" | "Ad Group" | "Ad">("Ad");
    const [loading, setLoading] = useState(false);
    const [rawData, setRawData] = useState<any[]>([]);
    const [apiColumns, setApiColumns] = useState<string[]>([]);
    const [visibleColumns, setVisibleColumns] = useState<Set<string>>(new Set());
    const [sortKey, setSortKey] = useState<string | null>(null);
    const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
    const [showColumnPicker, setShowColumnPicker] = useState(false);

    // Fetch data when platform or date range changes
    // Granularity change does NOT trigger fetch, only re-processing of valid columns/aggregation
    useEffect(() => {
        fetchData();
    }, [platform, startDate, endDate]);

    async function fetchData() {
        setLoading(true);
        try {
            const res = await fetch(
                `http://localhost:8000/api/v1/connectors/${platform}/hierarchy?mock_mode=true&start_date=${startDate}&end_date=${endDate}`
            );
            const json = await res.json();
            setRawData(json.data || []);
            setApiColumns(json.columns || []);
        } catch (err) {
            console.error("Failed to fetch:", err);
            setRawData([]);
            setApiColumns([]);
        }
        setLoading(false);
    }

    // Determine Valid Columns based on Granularity and API response
    // This implements the dynamic requirement
    const validColumns = (() => {
        if (!apiColumns.length) return [];

        return apiColumns.filter(key => {
            // Always show metrics
            if (METRIC_KEYS.has(key)) return true;

            // Filter dimensions based on granularity
            if (granularity === "Campaign") {
                // Only Campaign dimensions
                return key.startsWith("campaign_");
            } else if (granularity === "Ad Group") {
                // Campaign and Ad Group dimensions
                return key.startsWith("campaign_") ||
                    key.startsWith("ad_group_") ||
                    key.startsWith("ad_set_");
            } else {
                // All dimensions (Ad Level)
                return true;
            }
        }).map(key => {
            // Enhance with metadata
            const meta = COLUMN_METADATA[key];
            return {
                key,
                label: meta?.label || key.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase()), // Fallback label
                group: meta?.group || "Other",
                format: meta?.format
            };
        });
    })();

    // Initialize visible columns when validColumns changes (e.g. platform switch or fetch)
    // Only if visibleColumns is empty to respect user choice, OR if platform changed significantly
    useEffect(() => {
        if (validColumns.length > 0) {
            // Default: Show first 10 columns
            const defaultSet = new Set(validColumns.slice(0, 12).map(c => c.key));
            setVisibleColumns(defaultSet);
        }
    }, [platform, validColumns.length]);

    // Process data: Aggregation based on Granularity
    const processedData = (() => {
        if (!rawData.length) return [];

        if (granularity === "Ad") return rawData;

        // Grouping
        const groups: Record<string, any> = {};

        rawData.forEach(row => {
            // Determine grouping key
            const groupKey = granularity === "Campaign"
                ? row.campaign_id
                : (row.ad_group_id || row.ad_set_id); // Ad Group or Ad Set ID

            if (!groupKey) return; // Skip invalid rows

            if (!groups[groupKey]) {
                // Initialize with dimension fields
                groups[groupKey] = { ...row };
                // Reset metrics for accumulation
                groups[groupKey].ad_spend = 0;
                groups[groupKey].ad_impressions = 0;
                groups[groupKey].ad_clicks = 0;
                groups[groupKey].ad_conversions = 0;
            }

            // Sum metrics
            groups[groupKey].ad_spend += (row.ad_spend || 0);
            groups[groupKey].ad_impressions += (row.ad_impressions || 0);
            groups[groupKey].ad_clicks += (row.ad_clicks || 0);
            groups[groupKey].ad_conversions += (row.ad_conversions || 0);
        });

        // Recalculate computed metrics (CTR, CPC, etc.)
        return Object.values(groups).map(row => {
            const r = { ...row };
            r.ad_ctr = r.ad_impressions > 0 ? (r.ad_clicks / r.ad_impressions) * 100 : 0;
            r.ad_cpc = r.ad_clicks > 0 ? r.ad_spend / r.ad_clicks : 0;
            r.ad_cpa = r.ad_conversions > 0 ? r.ad_spend / r.ad_conversions : 0;

            // Note: Granular fields are filtered out by 'validColumns', so we don't strictly need to nullify them here,
            // but it's good practice for data cleanliness.

            return r;
        });
    })();

    // Sort data
    const sortedData = [...processedData].sort((a, b) => {
        if (!sortKey) return 0;
        const aVal = a[sortKey];
        const bVal = b[sortKey];
        if (aVal === bVal) return 0;
        const cmp = aVal < bVal ? -1 : 1;
        return sortDir === "asc" ? cmp : -cmp;
    });

    // Toggle column visibility
    function toggleColumn(key: string) {
        const next = new Set(visibleColumns);
        if (next.has(key)) next.delete(key);
        else next.add(key);
        setVisibleColumns(next);
    }

    // Export to CSV
    function exportCSV() {
        const colsToExport = validColumns.filter(c => visibleColumns.has(c.key));
        const headers = colsToExport.map(c => c.label).join(",");
        const rows = sortedData.map(row =>
            colsToExport.map(c => formatValue(row[c.key], c.format)).join(",")
        );
        const csv = [headers, ...rows].join("\n");
        const blob = new Blob([csv], { type: "text/csv" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${platform}_${granularity}_${startDate}_${endDate}.csv`;
        a.click();
    }

    const tableColumns = validColumns.filter(c => visibleColumns.has(c.key));

    // Get unique groups for column picker
    const columnGroups = Array.from(new Set(validColumns.map(c => c.group)));

    return (
        <SimpleLayout>
            <div className="p-6 space-y-6">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold text-foreground">Ad Platform Data Explorer</h1>
                        <p className="text-muted-foreground">View full hierarchy: Campaign → Ad Group/Set → Ad</p>
                    </div>
                    <button
                        onClick={exportCSV}
                        className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition flex items-center gap-2"
                    >
                        <span>📥</span> Export CSV
                    </button>
                </div>

                {/* Filters */}
                <div className="flex flex-wrap gap-4 p-4 bg-card rounded-xl border border-border items-end">
                    {/* Platform */}
                    <div className="flex flex-col gap-1">
                        <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Platform</label>
                        <select
                            value={platform}
                            onChange={(e) => setPlatform(e.target.value)}
                            className="px-3 py-2 bg-input border border-border rounded-lg text-foreground min-w-[150px]"
                        >
                            {PLATFORMS.map((p) => (
                                <option key={p.id} value={p.id}>
                                    {p.icon} {p.name}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* Date Range */}
                    <div className="flex flex-col gap-1">
                        <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Date Range</label>
                        <div className="flex items-center gap-2 bg-input border border-border rounded-lg px-2 py-1">
                            <input
                                type="date"
                                value={startDate}
                                onChange={(e) => setStartDate(e.target.value)}
                                className="bg-transparent text-foreground outline-none text-sm"
                            />
                            <span className="text-muted-foreground">→</span>
                            <input
                                type="date"
                                value={endDate}
                                onChange={(e) => setEndDate(e.target.value)}
                                className="bg-transparent text-foreground outline-none text-sm"
                            />
                        </div>
                    </div>

                    {/* Granularity */}
                    <div className="flex flex-col gap-1">
                        <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Granularity</label>
                        <select
                            value={granularity}
                            onChange={(e) => setGranularity(e.target.value as any)}
                            className="px-3 py-2 bg-input border border-border rounded-lg text-foreground min-w-[120px]"
                        >
                            <option value="Campaign">Campaign Level</option>
                            <option value="Ad Group">{platform.includes('meta') || platform.includes('linkedin') ? 'Ad Set' : 'Ad Group'} Level</option>
                            <option value="Ad">Ad Level</option>
                        </select>
                    </div>

                    {/* Column Picker */}
                    <div className="flex flex-col gap-1 relative">
                        <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Columns</label>
                        <button
                            onClick={() => setShowColumnPicker(!showColumnPicker)}
                            className="px-3 py-2 bg-input border border-border rounded-lg text-foreground text-left min-w-[150px] flex justify-between items-center"
                        >
                            <span>{visibleColumns.size} Columns</span>
                            <span className="text-xs opacity-50">▼</span>
                        </button>
                        {showColumnPicker && (
                            <div className="absolute top-full mt-1 z-50 w-72 max-h-96 overflow-y-auto bg-card border border-border rounded-lg shadow-xl p-4">
                                <div className="flex justify-between items-center mb-3 pb-2 border-b border-border">
                                    <span className="font-semibold text-sm">Select Columns</span>
                                    <button
                                        onClick={() => setShowColumnPicker(false)}
                                        className="text-xs bg-primary text-primary-foreground px-2 py-1 rounded hover:bg-primary/90"
                                    >
                                        Done
                                    </button>
                                </div>
                                {columnGroups.map((group) => {
                                    const groupCols = validColumns.filter((c) => c.group === group);
                                    if (groupCols.length === 0) return null;
                                    return (
                                        <div key={group} className="mb-4 last:mb-0">
                                            <div className="text-xs font-bold text-muted-foreground mb-2 uppercase tracking-wide">{group}</div>
                                            <div className="space-y-1">
                                                {groupCols.map((col) => (
                                                    <label key={col.key} className="flex items-center gap-2 py-1 cursor-pointer hover:bg-muted/50 rounded px-1 select-none">
                                                        <input
                                                            type="checkbox"
                                                            checked={visibleColumns.has(col.key)}
                                                            onChange={() => toggleColumn(col.key)}
                                                            className="rounded bg-background border-muted text-primary focus:ring-primary"
                                                        />
                                                        <span className="text-sm text-foreground">{col.label}</span>
                                                    </label>
                                                ))}
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </div>

                    {/* Refresh */}
                    <div className="ml-auto">
                        <button
                            onClick={fetchData}
                            disabled={loading}
                            className="px-6 py-2 bg-accent text-accent-foreground rounded-lg hover:bg-accent/90 transition disabled:opacity-50 font-medium"
                        >
                            {loading ? "Loading..." : "Refresh Data"}
                        </button>
                    </div>
                </div>

                {/* Granularity Notice */}
                <div className="flex items-center gap-2 text-sm text-muted-foreground bg-muted/20 p-2 rounded border border-white/5">
                    <span className="text-yellow-500">ℹ️</span>
                    Viewing data aggregated at <b>{granularity}</b> level from <b>{startDate}</b> to <b>{endDate}</b>.
                    Available columns dynamically adjusted based on granularity.
                </div>

                {/* Data Table */}
                <div className="bg-card rounded-xl border border-border overflow-hidden shadow-sm">
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead className="bg-muted/50">
                                <tr>
                                    {tableColumns.map((col) => (
                                        <th
                                            key={col.key}
                                            onClick={() => {
                                                if (sortKey === col.key) {
                                                    setSortDir(sortDir === "asc" ? "desc" : "asc");
                                                } else {
                                                    setSortKey(col.key);
                                                    setSortDir("desc");
                                                }
                                            }}
                                            className="px-4 py-3 text-left font-medium text-muted-foreground cursor-pointer hover:text-foreground whitespace-nowrap transition-colors"
                                        >
                                            <div className="flex items-center gap-1">
                                                {col.label}
                                                {sortKey === col.key && (
                                                    <span className="text-primary">{sortDir === "asc" ? "↑" : "↓"}</span>
                                                )}
                                            </div>
                                        </th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-border/50">
                                {loading ? (
                                    <tr>
                                        <td colSpan={tableColumns.length || 1} className="px-4 py-12 text-center text-muted-foreground">
                                            <div className="animate-pulse">Loading data...</div>
                                        </td>
                                    </tr>
                                ) : sortedData.length === 0 ? (
                                    <tr>
                                        <td colSpan={tableColumns.length || 1} className="px-4 py-12 text-center text-muted-foreground">
                                            No data available for this range
                                        </td>
                                    </tr>
                                ) : (
                                    sortedData.map((row, i) => (
                                        <tr key={i} className="hover:bg-muted/30 transition group">
                                            {tableColumns.map((col) => (
                                                <td key={col.key} className="px-4 py-3 text-foreground whitespace-nowrap group-hover:text-white">
                                                    {formatValue(row[col.key], col.format)}
                                                </td>
                                            ))}
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                    {/* Footer */}
                    <div className="px-4 py-3 bg-muted/30 border-t border-border flex items-center justify-between">
                        <span className="text-sm text-muted-foreground">
                            {sortedData.length} rows • {tableColumns.length} columns visible
                        </span>
                        <span className="text-xs text-muted-foreground opacity-50">
                            Mock Mode • {platform}
                        </span>
                    </div>
                </div>
            </div>
        </SimpleLayout>
    );
}
