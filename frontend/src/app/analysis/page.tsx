"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Loader2, TrendingUp, DollarSign, MousePointerClick, Eye, Target, Zap, ChevronDown, BarChart3, TrendingDown, Activity, Stethoscope, CheckCircle, AlertTriangle } from "lucide-react";
import { api } from "@/lib/api";

interface AggregatedMetrics {
    total_spend: number;
    total_impressions: number;
    total_clicks: number;
    total_conversions: number;
    avg_ctr: number;
    avg_cpc: number;
    avg_cpa: number;
    conversion_rate: number;
}

interface AnalysisConfig {
    use_rag_summary: boolean;
    include_benchmarks: boolean;
    analysis_depth: 'Quick' | 'Standard' | 'Deep';
    include_recommendations: boolean;
}

import { useAnalysis } from "@/context/AnalysisContext";

export default function GlobalAnalysisPage() {
    const {
        analyzing,
        analysisResult,
        config,
        setConfig,
        runAutoAnalysis
    } = useAnalysis();

    const [metrics, setMetrics] = useState<AggregatedMetrics | null>(null);
    const [healthCheckLoading, setHealthCheckLoading] = useState(false);
    const [healthCheckResult, setHealthCheckResult] = useState<any>(null);

    useEffect(() => {
        loadMetrics();
    }, []);

    const runHealthCheck = async () => {
        setHealthCheckLoading(true);
        setHealthCheckResult(null);
        try {
            const result = await api.post('/analyze/health-check', {});
            setHealthCheckResult(result);
        } catch (error) {
            console.error("Health check failed", error);
            setHealthCheckResult({ success: false, error: String(error) });
        } finally {
            setHealthCheckLoading(false);
        }
    };

    const loadMetrics = async () => {
        try {
            const metrics = await api.get('/campaigns/metrics') as AggregatedMetrics;
            setMetrics({
                total_spend: metrics.total_spend || 0,
                total_impressions: metrics.total_impressions || 0,
                total_clicks: metrics.total_clicks || 0,
                total_conversions: metrics.total_conversions || 0,
                avg_ctr: metrics.avg_ctr || 0,
                avg_cpc: metrics.avg_cpc || 0,
                avg_cpa: metrics.avg_cpa || 0,
                conversion_rate: metrics.total_conversions && metrics.total_clicks
                    ? (metrics.total_conversions / metrics.total_clicks) * 100
                    : 0
            });
        } catch (error) {
            console.error("Failed to load metrics", error);
        }
    };

    const formatNumber = (num: number): string => {
        if (num >= 1000000) return `${(num / 1000000).toFixed(2)}M`;
        if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
        return num.toLocaleString();
    };

    const formatCurrency = (num: number): string => {
        if (num >= 1000000) return `$${(num / 1000000).toFixed(2)}M`;
        if (num >= 1000) return `$${(num / 1000).toFixed(1)}K`;
        return `$${num.toFixed(2)}`;
    };

    // Render markdown-like text with proper formatting
    const renderMarkdown = (text: string) => {
        if (!text) return null;

        // Split into paragraphs/sections
        const mainSections = [
            "Performance Overview",
            "Performance vs Industry Benchmarks",
            "Multi-KPI Analysis",
            "Platform-Specific Insights",
            "Channel & Platform Analysis",
            "Funnel & Strategic Insights",
            "Ad Type & Creative Performance",
            "Audience & Demographic Insights",
            "What Is Working",
            "What Is Not Working",
            "Budget Optimization",
            "Optimization Roadmap",
            "Priority Actions",
            "Overall",
            "Overall Summary",
            "Channel Summary",
            "Key Strengths",
            "Key Strength",
            "The \"So What?\" Test",
            "Outcomes Over Activity",
            "Quantify Impact",
            "Root Cause Analysis",
            "Prescriptive Actions",
            "Strategic Recommendations"
        ];

        const sections = text.split(/\n\n+/);

        return sections.map((section: string, sIdx: number) => {
            // Check if it's a MAIN section header (starts with **Header:** and is in our list)
            if (section.startsWith('**') && section.includes(':**')) {
                const parts = section.split(':**');
                const headerText = parts[0].replace('**', '').trim();
                const contentText = parts.slice(1).join(':**').trim();

                if (mainSections.includes(headerText)) {
                    return (
                        <div key={sIdx} className="mt-8 mb-4">
                            <h3 className="text-xl font-bold text-violet-500 mb-3 border-b border-violet-500/10 pb-2 flex items-center gap-2">
                                <Target className="h-5 w-5" />
                                {headerText}
                            </h3>
                            {contentText && (
                                <div className="text-sm leading-relaxed text-muted-foreground pl-1">
                                    {renderInlineFormatting(contentText)}
                                </div>
                            )}
                        </div>
                    );
                }
            }

            // Standard Headers
            if (section.startsWith('### ')) {
                return <h3 key={sIdx} className="text-lg font-semibold mt-4 mb-2">{section.replace('### ', '')}</h3>;
            }
            if (section.startsWith('## ')) {
                return <h2 key={sIdx} className="text-xl font-bold mt-4 mb-2">{section.replace('## ', '')}</h2>;
            }
            if (section.startsWith('# ')) {
                return <h1 key={sIdx} className="text-2xl font-bold mt-4 mb-2">{section.replace('# ', '')}</h1>;
            }

            // Check if it's a list
            if (section.includes('\n- ') || section.startsWith('- ')) {
                const items = section.split('\n').filter((line: string) => line.trim());
                return (
                    <ul key={sIdx} className="list-disc ml-6 space-y-2 my-4">
                        {items.map((item: string, iIdx: number) => (
                            <li key={iIdx} className="text-sm text-muted-foreground pl-1">
                                {renderInlineFormatting(item.replace(/^-\s*/, ''))}
                            </li>
                        ))}
                    </ul>
                );
            }

            // Regular paragraph with inline formatting
            return (
                <p key={sIdx} className="mb-4 text-sm leading-relaxed text-muted-foreground last:mb-0">
                    {renderInlineFormatting(section)}
                </p>
            );
        });
    };

    // Render inline formatting (bold, italic)
    const renderInlineFormatting = (text: string) => {
        const parts = text.split(/(\*\*[^*]+\*\*)/g);
        return parts.map((part, idx) => {
            if (part.startsWith('**') && part.endsWith('**')) {
                return <strong key={idx} className="font-bold text-foreground">{part.slice(2, -2)}</strong>;
            }
            return part;
        });
    };



    return (
        <div className="container mx-auto py-10 px-6 space-y-10 max-w-7xl animate-in fade-in duration-700">
            <div className="flex items-center justify-between border-b pb-6">
                <div>
                    <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-r from-violet-500 to-indigo-500 bg-clip-text text-transparent">
                        🧠 AI Analysis
                    </h1>
                    <p className="text-muted-foreground mt-2 text-lg">
                        RAG-enhanced performance insights across all media campaigns.
                    </p>
                </div>
                {analyzing && <Badge variant="secondary" className="bg-violet-500/10 text-violet-500 animate-pulse border-violet-500/20 px-3 py-1">Running Intelligence...</Badge>}
            </div>

            {/* Analysis Configuration */}
            <Card className="border-violet-500/20 bg-violet-500/5 backdrop-blur-sm shadow-xl shadow-violet-500/5">
                <CardHeader>
                    <div className="flex items-center gap-3">
                        <div className="bg-violet-500 rounded-lg p-2">
                            <Zap className="h-5 w-5 text-white" />
                        </div>
                        <div>
                            <CardTitle className="text-xl">Configuration</CardTitle>
                            <CardDescription>Tailor the analysis depth and focus</CardDescription>
                        </div>
                    </div>
                </CardHeader>
                <CardContent className="space-y-8">
                    <div className="grid gap-8 md:grid-cols-2">
                        <div className="space-y-6">
                            <div className="flex items-start space-x-3 group">
                                <Checkbox
                                    id="rag"
                                    checked={config.use_rag_summary}
                                    onCheckedChange={(checked) => setConfig({ ...config, use_rag_summary: checked as boolean })}
                                    className="mt-1 data-[state=checked]:bg-violet-500 data-[state=checked]:border-violet-500"
                                />
                                <div className="space-y-1">
                                    <Label htmlFor="rag" className="text-sm font-semibold cursor-pointer group-hover:text-violet-500 transition-colors">
                                        Use RAG Intelligence
                                    </Label>
                                    <p className="text-xs text-muted-foreground leading-relaxed">
                                        Enhanced with verified marketing knowledge from your custom knowledge base.
                                    </p>
                                </div>
                            </div>

                            <div className="flex items-start space-x-3 group">
                                <Checkbox
                                    id="benchmarks"
                                    checked={config.include_benchmarks}
                                    onCheckedChange={(checked) => setConfig({ ...config, include_benchmarks: checked as boolean })}
                                    className="mt-1 data-[state=checked]:bg-violet-500 data-[state=checked]:border-violet-500"
                                />
                                <div className="space-y-1">
                                    <Label htmlFor="benchmarks" className="text-sm font-semibold cursor-pointer group-hover:text-violet-500 transition-colors">
                                        Industry Benchmarks
                                    </Label>
                                    <p className="text-xs text-muted-foreground leading-relaxed">
                                        Compare performance against verified standards for your sector.
                                    </p>
                                </div>
                            </div>
                        </div>

                        <div className="space-y-6">
                            <div className="space-y-3">
                                <Label htmlFor="depth" className="text-sm font-semibold">Intelligence Depth</Label>
                                <Select
                                    value={config.analysis_depth}
                                    onValueChange={(value: any) => setConfig({ ...config, analysis_depth: value })}
                                >
                                    <SelectTrigger id="depth" className="border-violet-500/20 focus:ring-violet-500 focus:border-violet-500">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="Quick">⚡ Quick Scan</SelectItem>
                                        <SelectItem value="Standard">⚖️ Standard Deep Dive</SelectItem>
                                        <SelectItem value="Deep">🧪 Exhaustive Analysis</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="flex items-start space-x-3 group">
                                <Checkbox
                                    id="recommendations"
                                    checked={config.include_recommendations}
                                    onCheckedChange={(checked) => setConfig({ ...config, include_recommendations: checked as boolean })}
                                    className="mt-1 data-[state=checked]:bg-violet-500 data-[state=checked]:border-violet-500"
                                />
                                <div className="space-y-1">
                                    <Label htmlFor="recommendations" className="text-sm font-semibold cursor-pointer group-hover:text-violet-500 transition-colors">
                                        Strategic Roadmap
                                    </Label>
                                    <p className="text-xs text-muted-foreground leading-relaxed">
                                        Generate actionable next steps and budget shifts.
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="flex gap-4">
                        <Button
                            onClick={runAutoAnalysis}
                            disabled={analyzing}
                            className="flex-1 bg-violet-600 hover:bg-violet-700 text-white font-bold h-12 rounded-xl transition-all hover:scale-[1.01] active:scale-[0.99] shadow-lg shadow-violet-600/20"
                        >
                            {analyzing ? (
                                <>
                                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                                    RAG Summary...
                                </>
                            ) : (
                                <>
                                    <Zap className="mr-2 h-5 w-5" />
                                    RAG Summary
                                </>
                            )}
                        </Button>
                        <Button
                            onClick={runHealthCheck}
                            disabled={healthCheckLoading}
                            className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white font-bold h-12 rounded-xl transition-all hover:scale-[1.01] active:scale-[0.99] shadow-lg shadow-emerald-600/20"
                        >
                            {healthCheckLoading ? (
                                <>
                                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                                    Running Health Check...
                                </>
                            ) : (
                                <>
                                    <Stethoscope className="mr-2 h-5 w-5" />
                                    Campaign Health Check
                                </>
                            )}
                        </Button>
                    </div>
                </CardContent>

            </Card>

            {/* Key Metrics Overview */}
            <div className="space-y-6">
                <div className="flex items-center gap-2">
                    <BarChart3 className="h-6 w-6 text-violet-500" />
                    <h2 className="text-2xl font-bold tracking-tight">Portfolio Summary</h2>
                </div>
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    {[
                        { title: "Portfolio Spend", val: formatCurrency(metrics?.total_spend || 0), icon: DollarSign },
                        { title: "Conversions", val: formatNumber(metrics?.total_conversions || 0), icon: Target },
                        { title: "Avg. Efficiency (CTR)", val: `${(metrics?.avg_ctr || 0).toFixed(2)}%`, icon: TrendingUp },
                        { title: "Portfolio CPA", val: formatCurrency(metrics?.avg_cpa || 0), icon: DollarSign },
                        { title: "Portfolio Clicks", val: formatNumber(metrics?.total_clicks || 0), icon: MousePointerClick },
                        { title: "Gross Impressions", val: formatNumber(metrics?.total_impressions || 0), icon: Eye },
                        { title: "Portfolio CPC", val: formatCurrency(metrics?.avg_cpc || 0), icon: DollarSign },
                        { title: "Conv. Rate", val: `${(metrics?.conversion_rate || 0).toFixed(2)}%`, icon: TrendingUp },
                    ].map((item, i) => (
                        <Card key={i} className="hover:border-violet-500/30 transition-colors bg-card shadow-sm border-border/60">
                            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">{item.title}</CardTitle>
                                <item.icon className="h-4 w-4 text-violet-400" />
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold tracking-tight">{item.val}</div>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            </div>

            {/* Health Check Results */}
            {healthCheckResult && (
                <Card className={`border-2 ${healthCheckResult.success ? 'border-emerald-500/30 bg-emerald-500/5' : 'border-red-500/30 bg-red-500/5'}`}>
                    <CardHeader>
                        <div className="flex items-center gap-3">
                            <div className={`rounded-lg p-2 ${healthCheckResult.success ? 'bg-emerald-500' : 'bg-red-500'}`}>
                                {healthCheckResult.success ? (
                                    <CheckCircle className="h-5 w-5 text-white" />
                                ) : (
                                    <AlertTriangle className="h-5 w-5 text-white" />
                                )}
                            </div>
                            <div>
                                <CardTitle className="text-xl">Campaign Health Check Results</CardTitle>
                                <CardDescription>
                                    {healthCheckResult.success
                                        ? `Completed in ${healthCheckResult.duration_seconds?.toFixed(2) || 0}s - ${healthCheckResult.steps?.length || 0} agents ran`
                                        : 'Health check encountered errors'}
                                </CardDescription>
                            </div>
                        </div>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        {/* Steps Status */}
                        <div className="flex flex-wrap gap-2">
                            {healthCheckResult.steps?.map((step: any, i: number) => (
                                <Badge
                                    key={i}
                                    variant={step.status === 'success' ? 'default' : step.status === 'skipped' ? 'secondary' : 'destructive'}
                                    className={step.status === 'success' ? 'bg-emerald-500' : ''}
                                >
                                    {step.step}: {step.status}
                                </Badge>
                            ))}
                        </div>

                        {/* Metrics */}
                        {healthCheckResult.metrics?.answer && (
                            <div className="space-y-2">
                                <h4 className="font-semibold text-sm uppercase tracking-wider text-muted-foreground">Metrics Analysis</h4>
                                <p className="text-sm leading-relaxed">{healthCheckResult.metrics.answer}</p>
                            </div>
                        )}

                        {/* Insights */}
                        {healthCheckResult.insights?.executive_summary && (
                            <div className="space-y-2">
                                <h4 className="font-semibold text-sm uppercase tracking-wider text-muted-foreground">AI Insights</h4>
                                <div className="text-sm leading-relaxed">
                                    {typeof healthCheckResult.insights.executive_summary === 'string'
                                        ? healthCheckResult.insights.executive_summary
                                        : (healthCheckResult.insights.executive_summary.brief || '')}
                                </div>
                            </div>
                        )}

                        {/* Recommendations */}
                        {healthCheckResult.all_recommendations?.length > 0 && (
                            <div className="space-y-2">
                                <h4 className="font-semibold text-sm uppercase tracking-wider text-muted-foreground">Recommendations</h4>
                                <ul className="space-y-1">
                                    {healthCheckResult.all_recommendations.slice(0, 5).map((rec: string, i: number) => (
                                        <li key={i} className="text-sm flex items-start gap-2">
                                            <span className="text-emerald-500 mt-1">→</span>
                                            {typeof rec === 'string' ? rec : JSON.stringify(rec)}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}

                        {/* Errors */}
                        {healthCheckResult.errors?.length > 0 && (
                            <div className="space-y-2">
                                <h4 className="font-semibold text-sm uppercase tracking-wider text-red-500">Errors</h4>
                                <ul className="space-y-1">
                                    {healthCheckResult.errors.map((err: string, i: number) => (
                                        <li key={i} className="text-sm text-red-500">{err}</li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </CardContent>
                </Card>
            )}

            {/* Analysis Results */}
            {!analysisResult && !analyzing && (
                <div className="flex flex-col items-center justify-center py-24 text-center border-2 border-dashed rounded-3xl border-border/50 bg-muted/20">
                    <div className="bg-muted rounded-full p-6 mb-6">
                        <Target className="h-12 w-12 text-muted-foreground/40" />
                    </div>
                    <h3 className="text-xl font-bold text-foreground mb-2">Ready for Performance Intelligence</h3>
                    <p className="text-muted-foreground max-w-sm mx-auto">
                        Configure your analysis options above and click run to generate RAG-enhanced insights for your campaigns.
                    </p>
                </div>
            )}

            {analysisResult && (
                <div className="space-y-10 animate-in slide-in-from-bottom-8 duration-1000">
                    {/* Executive Summary */}
                    {analysisResult.executive_summary && (
                        <Card className="overflow-hidden border-violet-500/20 shadow-2xl shadow-violet-500/5">
                            <div className="h-1.5 w-full bg-gradient-to-r from-violet-500 to-indigo-500" />
                            <CardHeader>
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-3">
                                        <div className="bg-violet-500/10 rounded-lg p-2">
                                            <TrendingUp className="h-5 w-5 text-violet-500" />
                                        </div>
                                        <CardTitle className="text-2xl">Executive Intelligence</CardTitle>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        {analysisResult.executive_summary.rag_metadata && (
                                            <Badge variant="outline" className="border-violet-500/30 text-violet-500 bg-violet-500/5 px-3">
                                                <Zap className="mr-1 h-3 w-3 fill-violet-500" />
                                                RAG SYNCED
                                            </Badge>
                                        )}
                                    </div>
                                </div>
                            </CardHeader>
                            <CardContent className="space-y-8 pt-4">
                                {/* Brief Summary */}
                                <div className="bg-muted/30 p-6 rounded-2xl border border-border/50 shadow-inner">
                                    <h4 className="text-xs font-bold text-violet-500 uppercase tracking-widest mb-4">Core Brief</h4>
                                    <div className="text-base font-medium leading-relaxed">
                                        {(() => {
                                            const summary = analysisResult.executive_summary;
                                            const text = typeof summary === 'string'
                                                ? summary
                                                : (summary?.brief || '');
                                            return typeof text === 'string' ? renderMarkdown(text) : null;
                                        })()}
                                    </div>
                                </div>


                                {/* Detailed Summary (Accordion Style for Parity) */}
                                {analysisResult.executive_summary.detailed && (
                                    <Accordion type="single" collapsible className="w-full">
                                        <AccordionItem value="detailed" className="border-none">
                                            <AccordionTrigger className="flex items-center justify-center gap-2 bg-violet-500/5 hover:bg-violet-500/10 text-violet-500 font-bold py-4 rounded-xl hover:no-underline transition-all">
                                                <ChevronDown className="h-5 w-5" />
                                                Detailed Insights
                                            </AccordionTrigger>
                                            <AccordionContent className="pt-8 px-2">
                                                <div className="grid grid-cols-1 gap-1 border-l-2 border-violet-500/10 pl-8">
                                                    {typeof analysisResult.executive_summary.detailed === 'string'
                                                        ? renderMarkdown(analysisResult.executive_summary.detailed)
                                                        : analysisResult.executive_summary.detailed}
                                                </div>
                                            </AccordionContent>
                                        </AccordionItem>
                                    </Accordion>
                                )}

                                {/* RAG Metadata Stats */}
                                {analysisResult.executive_summary.rag_metadata && (
                                    <div className="grid grid-cols-2 md:grid-cols-4 gap-6 pt-8 border-t border-border/40">
                                        <div className="space-y-1">
                                            <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Compute Burden</p>
                                            <p className="text-lg font-bold">
                                                {(analysisResult.executive_summary.rag_metadata.tokens_input +
                                                    analysisResult.executive_summary.rag_metadata.tokens_output).toLocaleString()} <span className="text-xs font-normal text-muted-foreground/60">tkns</span>
                                            </p>
                                        </div>
                                        <div className="space-y-1">
                                            <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Logic Engine</p>
                                            <p className="text-lg font-bold text-violet-500">{analysisResult.executive_summary.rag_metadata.model.split('-')[0].toUpperCase()}</p>
                                        </div>
                                        <div className="space-y-1">
                                            <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Inference Lag</p>
                                            <p className="text-lg font-bold">{analysisResult.executive_summary.rag_metadata.latency.toFixed(2)}<span className="text-xs font-normal text-muted-foreground/60">s</span></p>
                                        </div>
                                        <div className="space-y-1">
                                            <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Knowledge Base</p>
                                            <p className="text-lg font-bold">{analysisResult.executive_summary.rag_metadata.retrieval_count || 5} <span className="text-xs font-normal text-muted-foreground/60">Sources</span></p>
                                        </div>
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    )}

                    {/* Insights & Recommendations (Grid for Reflex Parity) */}
                    <div className="grid gap-8 lg:grid-cols-2">
                        {/* Key Insights (Grid Layout) */}
                        {analysisResult.insights && analysisResult.insights.length > 0 && (
                            <div className="space-y-6">
                                <div className="flex items-center gap-2">
                                    <Zap className="h-6 w-6 text-yellow-500" />
                                    <h3 className="text-2xl font-bold tracking-tight">Key Insights</h3>
                                </div>
                                <div className="grid sm:grid-cols-2 gap-4">
                                    {analysisResult.insights.map((insight: string, i: number) => (
                                        <Card key={i} className="bg-card/50 border-border/40 hover:border-yellow-500/20 transition-all duration-300 group">
                                            <CardContent className="p-5 flex gap-4">
                                                <div className="bg-yellow-500/10 rounded-full p-2 h-fit shrink-0 group-hover:scale-110 transition-transform">
                                                    <Zap className="h-4 w-4 text-yellow-500 fill-yellow-500" />
                                                </div>
                                                <p className="text-sm leading-relaxed">{insight}</p>
                                            </CardContent>
                                        </Card>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Strategic Recommendations (Styled Borders) */}
                        {config.include_recommendations && analysisResult.recommendations && analysisResult.recommendations.length > 0 && (
                            <div className="space-y-6">
                                <div className="flex items-center gap-2">
                                    <Target className="h-6 w-6 text-violet-500" />
                                    <h3 className="text-2xl font-bold tracking-tight">Strategic Recommendations</h3>
                                </div>
                                <div className="space-y-4">
                                    {analysisResult.recommendations.map((rec: any, i: number) => (
                                        <div
                                            key={i}
                                            className="group relative overflow-hidden rounded-2xl border border-violet-500/10 bg-card p-5 pl-6 shadow-sm transition-all hover:shadow-violet-500/5"
                                        >
                                            <div className="absolute left-0 top-0 h-full w-1.5 bg-violet-500 transition-all group-hover:w-2" />
                                            <div className="flex justify-between items-start mb-2">
                                                <span className="text-[10px] font-extrabold uppercase tracking-widest text-violet-500">
                                                    {rec.category || `Strategy Item ${i + 1}`}
                                                </span>
                                                {rec.priority && (
                                                    <Badge variant="secondary" className={`text-[10px] font-bold ${rec.priority.toLowerCase() === 'high' ? 'bg-red-500/10 text-red-500' : 'bg-violet-500/10 text-violet-500'}`}>
                                                        {rec.priority} PRIORITY
                                                    </Badge>
                                                )}
                                            </div>
                                            <p className="text-sm font-medium leading-relaxed">{rec.recommendation || rec}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>



                    {/* Industrial Benchmarking */}
                    {config.include_benchmarks && analysisResult.benchmarks && (
                        <Card className="bg-gradient-to-br from-violet-500/[0.02] to-indigo-500/[0.02] border-violet-500/10">
                            <CardHeader>
                                <div className="flex items-center gap-3">
                                    <div className="bg-violet-500/10 rounded-lg p-2">
                                        <TrendingUp className="h-5 w-5 text-violet-500" />
                                    </div>
                                    <CardTitle>Industry Benchmarking</CardTitle>
                                </div>
                            </CardHeader>
                            <CardContent>
                                <div className="grid gap-4">
                                    {Object.entries(analysisResult.benchmarks).map(([metric, data]: [string, any]) => (
                                        <div key={metric} className="flex flex-col md:flex-row md:items-center justify-between p-4 rounded-xl border border-border/60 bg-card hover:border-violet-500/20 transition-all">
                                            <div className="mb-4 md:mb-0">
                                                <p className="text-xs font-extrabold uppercase tracking-widest text-muted-foreground mb-1">{metric.replace(/_/g, ' ')}</p>
                                                <h5 className="font-bold text-lg">{data.your_value?.toFixed(2) || '0.00'}<span className="text-xs font-normal text-muted-foreground ml-1">Your Avg</span></h5>
                                            </div>

                                            <div className="h-px md:h-8 md:w-px bg-border/60 my-2 md:my-0" />

                                            <div className="flex items-center gap-8">
                                                <div className="text-center">
                                                    <p className="text-[10px] font-bold text-muted-foreground uppercase mb-1">Benchmark</p>
                                                    <p className="font-bold">{data.benchmark?.toFixed(2) || '0.00'}</p>
                                                </div>
                                                <div className="text-center">
                                                    <p className="text-[10px] font-bold text-muted-foreground uppercase mb-1">Delta</p>
                                                    <div className={`flex items-center gap-1 font-extrabold ${data.diff_pct > 0 ? 'text-green-500' : 'text-red-500'}`}>
                                                        {data.diff_pct > 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                                                        {data.diff_pct > 0 ? '+' : ''}{data.diff_pct?.toFixed(1)}%
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </CardContent>
                        </Card>
                    )}
                </div>
            )}
        </div>
    );
}
