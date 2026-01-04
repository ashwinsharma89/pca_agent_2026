"use client";

import { useState, useEffect } from "react";
import { Upload, FileUp, Database, Loader2, CheckCircle2, FileSpreadsheet } from "lucide-react";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

interface UploadMetrics {
    total_spend: number;
    total_clicks: number;
    total_impressions: number;
    total_conversions: number;
    avg_ctr: number;
}

interface SchemaInfo {
    column: string;
    dtype: string;
    null_count: number;
}

interface UploadResult {
    success: boolean;
    imported_count: number;
    message: string;
    summary?: UploadMetrics;
    schema?: SchemaInfo[];
    preview?: any[];
}

interface SheetInfo {
    name: string;
    row_count: number;
    column_count: number;
    error?: string;
}

interface SheetPreview {
    filename: string;
    sheets: SheetInfo[];
    default_sheet: string;
}

// Helper function to format large numbers
const formatNumber = (num: number): string => {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(2) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toLocaleString();
};

// Helper function to format cell values (handles dates, numbers, etc.)
const formatCellValue = (value: any): string => {
    if (value === null || value === undefined) return '';

    // Check if it's a date string (ISO format with time component)
    if (typeof value === 'string') {
        const dateMatch = value.match(/^\d{4}-\d{2}-\d{2}(T|\s|$)/);
        if (dateMatch) {
            const date = new Date(value);
            if (!isNaN(date.getTime())) {
                // Check if it's a month-level date (first day of month)
                if (date.getDate() === 1) {
                    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short' });
                }
                return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
            }
        }
    }

    return String(value);
};

export default function UploadPage() {
    // File Upload State
    const [file, setFile] = useState<File | null>(null);
    const [uploading, setUploading] = useState(false);
    const [status, setStatus] = useState<any | null>(null);
    const [result, setResult] = useState<any | null>(null);
    const [showSheetDialog, setShowSheetDialog] = useState(false);
    const [sheetPreview, setSheetPreview] = useState<{ filename: string; sheets: any[] } | null>(null);
    const [selectedSheet, setSelectedSheet] = useState<string>("");
    const [loadingSheets, setLoadingSheets] = useState(false);

    // Database Connection State
    const [selectedCategory, setSelectedCategory] = useState("warehouse");
    const [selectedConnector, setSelectedConnector] = useState<any | null>(null);
    const [connectionStatus, setConnectionStatus] = useState<"idle" | "testing" | "success" | "error">("idle");
    const [connectionMsg, setConnectionMsg] = useState("");
    const [isSaving, setIsSaving] = useState(false);
    const [formData, setFormData] = useState<Record<string, string>>({});
    const [configOpen, setConfigOpen] = useState(false);

    // Import Flow State
    const [view, setView] = useState<"config" | "tables">("config");
    const [tables, setTables] = useState<string[]>([]);
    const [selectedTable, setSelectedTable] = useState<string>("");
    const [importing, setImporting] = useState(false);

    const { token } = useAuth();

    // Load persisted upload result from localStorage on mount
    useEffect(() => {
        const savedResult = localStorage.getItem('lastUploadResult');
        const savedStatus = localStorage.getItem('lastUploadStatus');
        if (savedResult) {
            try {
                setResult(JSON.parse(savedResult));
            } catch (e) {
                console.error('Failed to parse saved upload result', e);
            }
        }
        if (savedStatus) {
            try {
                setStatus(JSON.parse(savedStatus));
            } catch (e) {
                console.error('Failed to parse saved upload status', e);
            }
        }
    }, []);

    // Persist upload result to localStorage when it changes
    useEffect(() => {
        if (result) {
            localStorage.setItem('lastUploadResult', JSON.stringify(result));
        }
        if (status) {
            localStorage.setItem('lastUploadStatus', JSON.stringify(status));
        }
    }, [result, status]);

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            const selectedFile = e.target.files[0];
            setFile(selectedFile);
            setStatus(null);
            setResult(null);

            // If it's an Excel file, preview sheets
            if (selectedFile.name.endsWith('.xlsx') || selectedFile.name.endsWith('.xls')) {
                await previewExcelSheets(selectedFile);
            }
        }
    };

    const previewExcelSheets = async (file: File) => {
        setLoadingSheets(true);
        try {
            const formData = new FormData();
            formData.append('file', file);

            const token = localStorage.getItem('token');
            const headers: HeadersInit = {};
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
            headers['X-CSRF-Token'] = 'v2-token-generation-pca';

            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/campaigns/upload/preview-sheets`, {
                method: 'POST',
                headers,
                body: formData,
            });

            if (!response.ok) {
                const errorText = await response.text();
                // console.error('Sheet preview failed:', response.status, errorText);
                throw new Error(`Failed to preview sheets: ${response.status}`);
            }

            const preview: SheetPreview = await response.json();
            setSheetPreview(preview);
            setSelectedSheet(preview.default_sheet);
            setShowSheetDialog(true);
        } catch (error: any) {
            console.error('Sheet preview error:', error);
            setStatus({
                type: 'error',
                message: `Failed to preview Excel sheets: ${error.message}. Try uploading directly.`
            });
        } finally {
            setLoadingSheets(false);
        }
    };

    const handleUpload = async (sheetName?: string) => {
        if (!file) return;

        setUploading(true);
        setStatus(null);
        setResult(null);
        setShowSheetDialog(false);

        try {
            const formData = new FormData();
            formData.append('file', file);

            // Add sheet_name if provided (for Excel files)
            if (sheetName) {
                formData.append('sheet_name', sheetName);
            }

            const token = localStorage.getItem('token');
            const headers: HeadersInit = {};
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
            headers['X-CSRF-Token'] = 'v2-token-generation-pca';

            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/campaigns/upload`, {
                method: 'POST',
                headers,
                body: formData,
            });

            if (!response.ok) {
                if (response.status === 401 && typeof window !== 'undefined') {
                    window.dispatchEvent(new CustomEvent('unauthorized'));
                }
                const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
                throw new Error(error.detail || 'Upload failed');
            }

            const uploadResult = await response.json();

            if (uploadResult.success) {
                setStatus({
                    type: 'success',
                    message: `Successfully imported ${uploadResult.imported_count} campaigns${sheetName ? ` from sheet "${sheetName}"` : ''}.`
                });
                setResult(uploadResult);

                // CRITICAL: Clear stale RAG analysis from previous file upload
                localStorage.removeItem('pca_analysis_result');
                console.log('Cleared stale RAG summary from localStorage');
            } else {
                throw new Error(uploadResult.message || "Upload failed");
            }

        } catch (error: any) {
            setStatus({
                type: 'error',
                message: error.message || "Failed to upload file."
            });
        } finally {
            setUploading(false);
        }
    };

    const handleUploadClick = () => {
        if (file && (file.name.endsWith('.xlsx') || file.name.endsWith('.xls')) && sheetPreview) {
            setShowSheetDialog(true);
        } else {
            handleUpload();
        }
    };

    // Database Connection Logic
    const DB_CATEGORIES = [
        { id: "platform", label: "Ad Platforms", icon: "📢" },
        { id: "warehouse", label: "Data Warehouses", icon: "🏭" },
        { id: "database", label: "SQL / NoSQL Databases", icon: "🗄️" },
        { id: "storage", label: "File & Object Storage", icon: "☁️" },
        { id: "vector", label: "Vector Databases", icon: "🧠" },
        { id: "services", label: "API Services", icon: "🔌" },
    ];

    const CONNECTORS = {
        platform: [
            { id: "google_ads", name: "Google Ads", icon: "🔵", fields: ["client_id", "client_secret", "developer_token", "refresh_token", "customer_id"] },
            { id: "meta_ads", name: "Meta Ads (FB/IG)", icon: "∞", fields: ["app_id", "app_secret", "access_token", "ad_account_id"] },
            { id: "linkedin_ads", name: "LinkedIn Ads", icon: "💼", fields: ["client_id", "client_secret", "access_token", "ad_account_id"] },
            { id: "tiktok_ads", name: "TikTok Ads", icon: "🎵", fields: ["app_id", "secret", "access_token", "advertiser_id"] },
            { id: "snapchat_ads", name: "Snapchat Ads", icon: "👻", fields: ["client_id", "client_secret", "refresh_token", "ad_account_id"] },
            { id: "youtube", name: "YouTube Analytics", icon: "▶️", fields: ["client_id", "client_secret", "refresh_token", "channel_id"] },
            { id: "cm360", name: "Campaign Manager 360", icon: "🎯", fields: ["client_id", "client_secret", "refresh_token", "profile_id"] },
            { id: "dv360", name: "Display & Video 360", icon: "📺", fields: ["client_id", "client_secret", "refresh_token", "partner_id"] },
            { id: "microsoft_ads", name: "Microsoft Ads", icon: "🟦", fields: ["client_id", "developer_token", "refresh_token", "account_id"] },
            { id: "amazon_ads", name: "Amazon Ads", icon: "🛒", fields: ["client_id", "client_secret", "refresh_token", "profile_id"] },
            { id: "pinterest_ads", name: "Pinterest Ads", icon: "📌", fields: ["app_id", "access_token", "ad_account_id"] },
            { id: "twitter_ads", name: "X (Twitter) Ads", icon: "❌", fields: ["api_key", "api_secret", "access_token", "account_id"] },
        ],
        warehouse: [
            { id: "snowflake", name: "Snowflake", icon: "❄️", fields: ["account", "warehouse", "database", "schema", "username", "password", "role"] },
            { id: "databricks", name: "Databricks", icon: "🧱", fields: ["host", "http_path", "token", "catalog"] },
            { id: "redshift", name: "AWS Redshift", icon: "🔴", fields: ["host", "port", "database", "username", "password"] },
            { id: "bigquery", name: "Google BigQuery", icon: "🔍", fields: ["project_id", "dataset", "credentials_json"] },
            { id: "azure_synapse", name: "Azure Synapse", icon: "🔷", fields: ["host", "database", "username", "password"] },
        ],
        database: [
            { id: "postgresql", name: "PostgreSQL", icon: "🐘", fields: ["host", "port", "database", "username", "password"] },
            { id: "mysql", name: "MySQL", icon: "🐬", fields: ["host", "port", "database", "username", "password"] },
            { id: "clickhouse", name: "ClickHouse", icon: "📊", fields: ["host", "port", "database", "username", "password"] },
            { id: "duckdb", name: "DuckDB", icon: "🦆", fields: ["file_path_or_memory"] },
            { id: "mongodb", name: "MongoDB", icon: "🍃", fields: ["connection_string", "database"] },
            { id: "supabase", name: "Supabase", icon: "⚡", fields: ["host", "port", "database", "username", "password", "connection_string"] },
            { id: "cassandra", name: "Cassandra", icon: "👁️", fields: ["host", "port", "keyspace", "username", "password"] },
            { id: "dynamodb", name: "DynamoDB", icon: "📦", fields: ["region", "access_key", "secret_key"] },
            { id: "apache", name: "Apache Hive/Impala", icon: "🐘", fields: ["host", "port", "database"] },
        ],
        storage: [
            { id: "s3", name: "AWS S3", icon: "🪣", fields: ["bucket", "region", "access_key", "secret_key"] },
            { id: "gcs", name: "Google Cloud Storage", icon: "📦", fields: ["bucket", "credentials_json"] },
            { id: "azure_blob", name: "Azure Blob Storage", icon: "☁️", fields: ["container", "connection_string"] },
            { id: "sftp", name: "SFTP Server", icon: "📂", fields: ["host", "port", "username", "password"] },
        ],
        vector: [
            { id: "pinecone", name: "Pinecone", icon: "🌲", fields: ["api_key", "environment", "index_name"] },
            { id: "milvus", name: "Milvus", icon: "🕊️", fields: ["host", "port", "token"] },
            { id: "qdrant", name: "Qdrant", icon: "🟣", fields: ["url", "api_key"] },
            { id: "weaviate", name: "Weaviate", icon: "W", fields: ["url", "api_key"] },
            { id: "chromadb", name: "ChromaDB", icon: "🌈", fields: ["host", "port"] },
        ],
        services: [
            { id: "mailgun", name: "Mailgun (Email)", icon: "📧", fields: ["api_key", "domain", "region"] },
        ]
    };

    const handleConnectorClick = (connector: any) => {
        setSelectedConnector(connector);

        // Try to load persisted credentials
        const savedCreds = localStorage.getItem(`connector_creds_${connector.id}`);
        if (savedCreds) {
            try {
                setFormData(JSON.parse(savedCreds));
            } catch (e) {
                console.error("Failed to parse saved credentials", e);
                setFormData({});
            }
        } else {
            setFormData({});
        }

        setConnectionStatus("idle");
        setConnectionMsg("");
        setIsSaving(false);
        setIsSaving(false);
        setView("config");
        setTables([]);
        setSelectedTable("");
        setConfigOpen(true);
    };

    const handleFormChange = (key: string, value: string) => {
        setFormData(prev => ({ ...prev, [key]: value }));
    };

    const handleTestConnection = async () => {
        setConnectionStatus("testing");
        setConnectionMsg("");

        try {
            const token = localStorage.getItem('token');
            const headers: HeadersInit = { 'Content-Type': 'application/json' };
            if (token) headers['Authorization'] = `Bearer ${token}`;

            const payload = {
                category: selectedCategory,
                type: selectedConnector.id,
                ...formData
            };

            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/databases/test-connection`, {
                method: 'POST',
                headers,
                body: JSON.stringify(payload),
            });

            const data = await response.json();

            if (data.success) {
                setConnectionStatus("success");
                setConnectionMsg("Successfully connected!");
            } else {
                setConnectionStatus("error");
                setConnectionMsg(data.message || "Connection failed");
            }
        } catch (err: any) {
            setConnectionStatus("error");
            setConnectionMsg(err.message || "Network error");
        }
    };

    const handleListTables = async (connectionPayload: any) => {
        try {
            const token = localStorage.getItem('token');
            const headers: HeadersInit = { 'Content-Type': 'application/json' };
            if (token) headers['Authorization'] = `Bearer ${token}`;

            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/databases/tables`, {
                method: 'POST',
                headers,
                body: JSON.stringify(connectionPayload),
            });

            const data = await response.json();
            if (data.success) {
                setTables(data.tables || []);
                setView("tables");
                setConnectionMsg("");
            } else {
                setConnectionStatus("error");
                setConnectionMsg(data.message || "Failed to list tables");
            }
        } catch (err: any) {
            setConnectionStatus("error");
            setConnectionMsg(err.message || "Network error fetching tables");
        }
    };

    const handleImportTable = async () => {
        if (!selectedTable) return;
        setImporting(true);
        setStatus(null);

        try {
            const token = localStorage.getItem('token');
            const headers: HeadersInit = { 'Content-Type': 'application/json' };
            if (token) headers['Authorization'] = `Bearer ${token}`;

            const payload = {
                category: selectedCategory,
                type: selectedConnector.id,
                ...formData
            };

            // Call import endpoint
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/databases/import?table_name=${selectedTable}`, {
                method: 'POST',
                headers,
                body: JSON.stringify(payload),
            });

            const data = await response.json();

            if (data.success) {
                setConfigOpen(false); // Close modal
                setResult(data);
                setStatus({
                    type: 'success',
                    message: `Successfully imported ${data.imported_count} rows from ${selectedTable}.`
                });

                // CRITICAL: Clear stale RAG analysis from previous data import
                localStorage.removeItem('pca_analysis_result');
                console.log('Cleared stale RAG summary from localStorage (DB import)');
            } else {
                setConnectionStatus("error");
                setConnectionMsg(data.message || "Import failed");
            }

        } catch (err: any) {
            setConnectionStatus("error");
            setConnectionMsg(err.message || "Network error during import");
        } finally {
            setImporting(false);
        }
    };

    const handleSaveConnection = async () => {
        setIsSaving(true);
        try {
            const token = localStorage.getItem('token');
            const headers: HeadersInit = { 'Content-Type': 'application/json' };
            if (token) headers['Authorization'] = `Bearer ${token}`;

            const payload = {
                category: selectedCategory,
                type: selectedConnector.id,
                ...formData
            };

            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/databases/save-connection`, {
                method: 'POST',
                headers,
                body: JSON.stringify(payload),
            });

            const data = await response.json();

            if (data.success) {
                // Save credentials to localStorage
                localStorage.setItem(`connector_creds_${selectedConnector.id}`, JSON.stringify(formData));

                // Instead of closing, switch to Table Selection view
                setConnectionStatus("success");
                setConnectionMsg("Connected & Saved! Fetching tables...");

                // Fetch tables
                await handleListTables(payload);
            } else {
                setConnectionMsg(data.message || "Save failed");
                setConnectionStatus("error");
            }
        } catch (err: any) {
            setConnectionMsg(err.message || "Network error during save");
            setConnectionStatus("error");
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <div className="container mx-auto py-10 space-y-8">
            <h1 className="text-3xl font-bold tracking-tight">📊 Data Ingestion</h1>

            {/* Excel Sheet Selection Dialog */}
            <Dialog open={showSheetDialog} onOpenChange={setShowSheetDialog}>
                <DialogContent className="sm:max-w-[500px]">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <FileSpreadsheet className="h-5 w-5" />
                            Select Excel Sheet
                        </DialogTitle>
                        <DialogDescription>
                            This Excel file contains multiple sheets. Please select which sheet to upload.
                        </DialogDescription>
                    </DialogHeader>

                    {sheetPreview && (
                        <div className="space-y-4 py-4">
                            <div className="space-y-2">
                                <Label htmlFor="sheet-select">Sheet</Label>
                                <Select value={selectedSheet} onValueChange={setSelectedSheet}>
                                    <SelectTrigger id="sheet-select">
                                        <SelectValue placeholder="Select a sheet" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {sheetPreview.sheets.map((sheet) => (
                                            <SelectItem key={sheet.name} value={sheet.name}>
                                                {sheet.name} - {sheet.error ? '⚠️ Error' : `${sheet.row_count} rows, ${sheet.column_count} cols`}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                            {selectedSheet && (
                                <div className="rounded-md bg-muted p-3 text-sm">
                                    <div className="space-y-1">
                                        <p><strong>Sheet:</strong> {selectedSheet}</p>
                                        <p><strong>Rows:</strong> {sheetPreview.sheets.find(s => s.name === selectedSheet)?.row_count.toLocaleString()}</p>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    <DialogFooter className="relative z-[100]">
                        <Button type="button" variant="outline" onClick={() => setShowSheetDialog(false)}>
                            Cancel
                        </Button>
                        <Button
                            type="button"
                            onClick={() => handleUpload(selectedSheet)}
                            disabled={!selectedSheet || uploading}
                        >
                            {uploading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Upload className="mr-2 h-4 w-4" />}
                            Upload
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Database Configuration Dialog */}
            <Dialog open={configOpen} onOpenChange={setConfigOpen}>
                <DialogContent className="sm:max-w-[600px]">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <span className="text-2xl">{selectedConnector?.icon}</span>
                            Connect to {selectedConnector?.name}
                        </DialogTitle>
                        <DialogDescription>
                            Enter your credentials to establish a secure connection.
                        </DialogDescription>
                    </DialogHeader>

                    <div className="space-y-4 py-4">
                        {view === "config" ? (
                            <div className="grid grid-cols-2 gap-4">
                                {selectedConnector?.fields.map((field: string) => (
                                    <div key={field} className={`space-y-1 ${field === 'connection_string' ? 'col-span-2' : ''}`}>
                                        <Label className="capitalize">
                                            {field === 'connection_string' ? 'Connection URI (Optional, overrides fields)' : field.replace(/_/g, " ")}
                                        </Label>
                                        <Input
                                            type={field.includes('password') || field.includes('secret') || field.includes('key') || field.includes('token') ? "password" : "text"}
                                            placeholder={field === 'connection_string' ? "postgres://user:password@host:port/db" : `Enter ${field.replace(/_/g, " ")}`}
                                            value={formData[field] || ''}
                                            onChange={(e) => handleFormChange(field, e.target.value)}
                                        />
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="space-y-4">
                                <Label>Select Table to Import</Label>
                                {tables.length > 0 ? (
                                    <Select value={selectedTable} onValueChange={setSelectedTable}>
                                        <SelectTrigger>
                                            <SelectValue placeholder="Select a table..." />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {tables.map(t => (
                                                <SelectItem key={t} value={t}>{t}</SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                ) : (
                                    <div className="text-sm text-muted-foreground p-4 border border-dashed rounded-md text-center">
                                        No tables found in this database.
                                    </div>
                                )}

                                <div className="text-xs text-muted-foreground">
                                    <p>Select a table to ingest its data into the Analytics Engine.</p>
                                </div>
                            </div>
                        )}

                        {connectionStatus !== 'idle' && (
                            <Alert variant={connectionStatus === 'success' ? 'default' : connectionStatus === 'error' ? 'destructive' : 'default'} className={connectionStatus === 'success' ? 'border-green-500 bg-green-50/50' : ''}>
                                {connectionStatus === 'testing' && <Loader2 className="h-4 w-4 animate-spin" />}
                                {connectionStatus === 'success' && <CheckCircle2 className="h-4 w-4 text-green-600" />}
                                <AlertTitle>
                                    {connectionStatus === 'testing' ? "Connecting..." : connectionStatus === 'success' ? "Success" : "Error"}
                                </AlertTitle>
                                <AlertDescription>{connectionMsg}</AlertDescription>
                            </Alert>
                        )}
                    </div>

                    <DialogFooter>
                        {view === "config" ? (
                            <>
                                <Button variant="ghost" onClick={() => setConfigOpen(false)}>Cancel</Button>
                                <Button variant="outline" onClick={handleTestConnection} disabled={connectionStatus === 'testing' || isSaving}>
                                    {connectionStatus === 'testing' ? "Testing..." : "Test Connection"}
                                </Button>
                                <Button onClick={handleSaveConnection} disabled={connectionStatus !== 'success' || isSaving}>
                                    {isSaving ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Saving...</> : "Save & Continue"}
                                </Button>
                            </>
                        ) : (
                            <>
                                <Button variant="ghost" onClick={() => setView("config")}>Back</Button>
                                <Button onClick={handleImportTable} disabled={!selectedTable || importing}>
                                    {importing ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Importing...</> : "Import Data"}
                                </Button>
                            </>
                        )}
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {result && result.summary ? (
                // SUCCESS VIEW
                <div className="space-y-6 animate-in fade-in slide-in-from-bottom-5">
                    <div className="flex items-center justify-between">
                        <Alert className="border-green-500 text-green-700 bg-green-50 dark:bg-green-900/10 flex-1 mr-4">
                            <CheckCircle2 className="h-4 w-4" />
                            <AlertTitle>Upload Complete</AlertTitle>
                            <AlertDescription>{result.message}</AlertDescription>
                        </Alert>
                        <Button variant="outline" onClick={() => { setFile(null); setResult(null); setStatus(null); }}>
                            New Upload
                        </Button>
                    </div>
                    {/* Metrics Cards */}
                    <div className="grid gap-4 md:grid-cols-4">
                        <Card><CardHeader className="pb-2"><CardTitle className="text-sm font-medium text-muted-foreground">Total Spend</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">${formatNumber(result.summary.total_spend)}</div></CardContent></Card>
                        <Card><CardHeader className="pb-2"><CardTitle className="text-sm font-medium text-muted-foreground">Total Clicks</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{formatNumber(result.summary.total_clicks)}</div></CardContent></Card>
                        <Card><CardHeader className="pb-2"><CardTitle className="text-sm font-medium text-muted-foreground">Conversions</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{formatNumber(result.summary.total_conversions)}</div></CardContent></Card>
                        <Card><CardHeader className="pb-2"><CardTitle className="text-sm font-medium text-muted-foreground">Avg CTR</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{result.summary.avg_ctr.toFixed(2)}%</div></CardContent></Card>
                    </div>

                    {/* Data Quality & Schema */}
                    {result.schema && (
                        <Card>
                            <CardHeader className="pb-2">
                                <CardTitle className="flex items-center gap-2">
                                    <CheckCircle2 className="h-5 w-5 text-emerald-500" />
                                    Dataset Schema & Quality
                                </CardTitle>
                                <CardDescription>
                                    Found {result.schema.length} columns. Review data types and missing values below.
                                </CardDescription>
                            </CardHeader>
                            <CardContent>
                                <div className="rounded-md border">
                                    <Table>
                                        <TableHeader className="bg-muted/50">
                                            <TableRow>
                                                <TableHead>Column Name</TableHead>
                                                <TableHead>Data Type</TableHead>
                                                <TableHead>Null Count</TableHead>
                                                <TableHead>Status</TableHead>
                                            </TableRow>
                                        </TableHeader>
                                        <TableBody>
                                            {result.schema.map((col: SchemaInfo) => (
                                                <TableRow key={col.column}>
                                                    <TableCell className="font-medium">{col.column}</TableCell>
                                                    <TableCell>
                                                        <span className="inline-flex items-center px-2 py-1 rounded-md bg-muted text-xs font-medium font-mono">
                                                            {col.dtype}
                                                        </span>
                                                    </TableCell>
                                                    <TableCell>{col.null_count}</TableCell>
                                                    <TableCell>
                                                        {col.null_count === 0 ? (
                                                            <div className="flex items-center text-emerald-600 text-xs font-medium">
                                                                <CheckCircle2 className="mr-1 h-3 w-3" />
                                                                Clean
                                                            </div>
                                                        ) : (
                                                            <div className="flex items-center text-amber-600 text-xs font-medium">
                                                                <AlertTitle className="mr-1 h-3 w-3">⚠️</AlertTitle>
                                                                {col.null_count} Missing
                                                            </div>
                                                        )}
                                                    </TableCell>
                                                </TableRow>
                                            ))}
                                        </TableBody>
                                    </Table>
                                </div>
                            </CardContent>
                        </Card>
                    )}
                    {/* Data Preview */}
                    <Card className="overflow-hidden">
                        <CardHeader><CardTitle>Data Preview</CardTitle></CardHeader>
                        <CardContent className="h-[300px] overflow-y-auto">
                            <Table>
                                <TableHeader><TableRow>{result.schema?.map((c: any) => <TableHead key={c.column}>{c.column}</TableHead>)}</TableRow></TableHeader>
                                <TableBody>{result.preview?.map((r: any, i: number) => <TableRow key={i}>{result.schema?.map((c: any) => <TableCell key={c.column}>{formatCellValue(r[c.column])}</TableCell>)}</TableRow>)}</TableBody>
                            </Table>
                        </CardContent>
                    </Card>
                </div>
            ) : (
                // MAIN SPLIT VIEW
                <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-2 items-start">
                    {/* LEFT: FILE UPLOAD */}
                    <Card className="h-full border-2 border-dashed border-muted-foreground/20 hover:border-muted-foreground/40 transition-colors">
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <FileUp className="h-5 w-5 text-blue-500" />
                                File Upload
                            </CardTitle>
                            <CardDescription>
                                Upload campaign data (CSV/Excel).
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            <div className="flex flex-col items-center justify-center space-y-4 py-8">
                                <div className="p-4 bg-muted rounded-full">
                                    <Upload className="h-8 w-8 text-muted-foreground" />
                                </div>
                                <div className="text-center space-y-1">
                                    <p className="font-medium">Drag & drop or click to upload</p>
                                    <p className="text-xs text-muted-foreground">Required: Campaign, Platform, Spend, Impressions</p>
                                </div>
                                <Input
                                    id="campaign-file"
                                    type="file"
                                    accept=".csv,.xlsx,.xls"
                                    onChange={handleFileChange}
                                    className="max-w-xs"
                                />
                            </div>

                            {file && sheetPreview && (
                                <div className="rounded-md bg-muted p-3 text-sm flex items-center gap-2">
                                    <FileSpreadsheet className="h-4 w-4 text-green-600" />
                                    <span className="font-medium">{sheetPreview.filename}</span>
                                    <span className="text-muted-foreground text-xs">({sheetPreview.sheets.length} sheets)</span>
                                </div>
                            )}

                            {status && <Alert variant={status.type === 'error' ? "destructive" : "default"}><AlertTitle>{status.type === 'success' ? "Success" : "Error"}</AlertTitle><AlertDescription>{status.message}</AlertDescription></Alert>}

                            <Button onClick={handleUploadClick} disabled={!file || uploading || loadingSheets} className="w-full">
                                {uploading ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Uploading...</> : 'Import Data'}
                            </Button>
                        </CardContent>
                    </Card>

                    {/* RIGHT: DATABASE CONNECTIONS */}
                    <Card className="h-full flex flex-col">
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <Database className="h-5 w-5 text-purple-500" />
                                Database Connections
                            </CardTitle>
                            <CardDescription>
                                Connect to external data sources.
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="flex-1">
                            {/* Categories Pills */}
                            <div className="flex flex-wrap gap-2 mb-6">
                                {DB_CATEGORIES.map(cat => (
                                    <button
                                        key={cat.id}
                                        onClick={() => setSelectedCategory(cat.id)}
                                        className={`px-3 py-1 text-xs font-medium rounded-full transition-all border ${selectedCategory === cat.id ? "bg-primary text-primary-foreground border-primary" : "bg-card hover:bg-muted text-muted-foreground border-border"}`}
                                    >
                                        <span className="mr-1">{cat.icon}</span>
                                        {cat.label.split(" ")[0]}
                                    </button>
                                ))}
                            </div>

                            {/* Connectors Grid */}
                            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                                {CONNECTORS[selectedCategory as keyof typeof CONNECTORS]?.map(conn => (
                                    <button
                                        key={conn.id}
                                        onClick={() => handleConnectorClick(conn)}
                                        className="flex flex-col items-center justify-center p-4 rounded-lg border border-border/50 hover:border-primary/50 hover:bg-muted/50 transition-all group h-28"
                                    >
                                        <span className="text-3xl mb-2 group-hover:scale-110 transition-transform">{conn.icon}</span>
                                        <span className="text-xs font-medium text-center truncate w-full">{conn.name}</span>
                                    </button>
                                ))}
                            </div>
                        </CardContent>
                        <CardFooter className="border-t bg-muted/20 p-4">
                            <p className="text-xs text-center text-muted-foreground w-full">
                                Secure credentials are never stored in plain text.
                            </p>
                        </CardFooter>
                    </Card>
                </div>
            )}
        </div>
    );
}
