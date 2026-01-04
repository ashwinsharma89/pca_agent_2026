const getBaseUrl = () => {
    if (typeof window !== 'undefined') {
        // Client-side: Use configured public URL or localhost default
        return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
    }
    // Server-side (SSR):
    // 1. Prefer explicit internal URL if set
    if (process.env.INTERNAL_API_URL) return process.env.INTERNAL_API_URL;

    // 2. Intelligent Fallback:
    // If public URL is relative (e.g. "/api/v1" behind Nginx), we MUST use the internal Docker service URL
    if (process.env.NEXT_PUBLIC_API_URL?.startsWith('/')) {
        return 'http://api:8000/api/v1';
    }

    // 3. Default for local dev
    return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
};

const API_URL = getBaseUrl();

type RequestMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';

interface ApiRequestOptions extends RequestInit {
    token?: string;
}

export class ApiError extends Error {
    constructor(public status: number, public message: string, public data?: unknown) {
        super(message);
        this.name = 'ApiError';
    }
}

async function request<T>(endpoint: string, method: RequestMethod, body?: unknown, options?: ApiRequestOptions): Promise<T> {
    const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        'X-CSRF-Token': 'v2-token-generation-pca', // Add static CSRF token for defense-in-depth
        ...(options?.headers as Record<string, string>),
    };

    // Auto-inject token from localStorage if not explicitly provided
    const token = options?.token || (typeof window !== 'undefined' ? localStorage.getItem('token') : null);
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const config: RequestInit = {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
        ...options,
    };

    try {
        const response = await fetch(`${API_URL}${endpoint}`, config);

        if (!response.ok) {
            // Handle 401 Unauthorized - Session Expired
            if (response.status === 401) {
                // Dispatch custom event for session expiration
                if (typeof window !== 'undefined') {
                    window.dispatchEvent(new CustomEvent('unauthorized'));
                }
            }

            let errorMessage = 'An error occurred';
            let errorData = null;
            try {
                const errorBody = await response.json();
                errorMessage = errorBody.detail || errorBody.message || errorMessage;
                errorData = errorBody;
            } catch {
                // Ignore JSON parse error for error responses
            }
            throw new ApiError(response.status, errorMessage, errorData);
        }

        // Handle 204 No Content
        if (response.status === 204) {
            return {} as T;
        }

        return await response.json();
    } catch (error) {
        if (error instanceof ApiError) {
            throw error;
        }
        throw new Error('Network error or invalid JSON response');
    }
}

export interface ChatResponse {
    response: string;
    suggestedQueries?: string[];
    data?: unknown;
}

export interface Insight {
    id: string;
    title: string;
    description: string;
    severity: 'info' | 'warning' | 'error';
    metric?: string;
    change?: number;
}

export const api = {
    // Generic request method for flexibility
    request: <T>(endpoint: string, options?: ApiRequestOptions & { method?: RequestMethod; body?: unknown }) =>
        request<T>(endpoint, options?.method || 'GET', options?.body, options),

    get: <T>(endpoint: string, options?: ApiRequestOptions) => request<T>(endpoint, 'GET', undefined, options),
    async regenerateReport<T = unknown>(campaignId: string, template: string = 'default'): Promise<T> {
        return request<T>(`/campaigns/${campaignId}/report/regenerate`, 'POST', { template });
    },
    async chatWithCampaign(campaignId: string, question: string): Promise<ChatResponse> {
        return request<ChatResponse>(`/campaigns/${campaignId}/chat`, 'POST', { question });
    },
    async getCampaignInsights(campaignId: string): Promise<Insight[]> {
        return request<Insight[]>(`/campaigns/${campaignId}/insights`, 'GET');
    },
    async getCampaignVisualizations<T = unknown>(campaignId: string): Promise<T> {
        return request<T>(`/campaigns/${campaignId}/visualizations`, 'GET');
    },
    async getGlobalVisualizations<T = unknown>(filters?: {
        platforms?: string;
        startDate?: string;
        endDate?: string;
        primaryMetric?: string;
        secondaryMetric?: string;
        funnelStages?: string;
        channels?: string;
        devices?: string;
        placements?: string;
        regions?: string;
        adTypes?: string;
    }): Promise<T> {
        const params = new URLSearchParams();
        if (filters?.platforms) {
            params.append('platforms', filters.platforms);
        }
        if (filters?.startDate) {
            params.append('start_date', filters.startDate);
        }
        if (filters?.endDate) {
            params.append('end_date', filters.endDate);
        }
        if (filters?.primaryMetric) {
            params.append('primary_metric', filters.primaryMetric);
        }
        if (filters?.secondaryMetric) {
            params.append('secondary_metric', filters.secondaryMetric);
        }
        if (filters?.funnelStages) {
            params.append('funnel_stages', filters.funnelStages);
        }
        if (filters?.channels) {
            params.append('channels', filters.channels);
        }
        if (filters?.devices) {
            params.append('devices', filters.devices);
        }
        if (filters?.placements) {
            params.append('placements', filters.placements);
        }
        if (filters?.regions) {
            params.append('regions', filters.regions);
        }
        if (filters?.adTypes) {
            params.append('adTypes', filters.adTypes);
        }
        const queryString = params.toString();
        return request<T>(`/campaigns/visualizations${queryString ? `?${queryString}` : ''}`, 'GET');
    },
    async chatGlobal(question: string, options?: { knowledge_mode?: boolean; use_rag_context?: boolean }): Promise<ChatResponse> {
        return request<ChatResponse>(`/campaigns/chat`, 'POST', {
            question,
            knowledge_mode: options?.knowledge_mode ?? false,
            use_rag_context: options?.use_rag_context ?? true
        });
    },
    async analyzeGlobal<T = unknown>(): Promise<T> {
        return request<T>(`/campaigns/analyze/global`, 'POST');
    },
    async getSchema<T = unknown>(): Promise<T> {
        return request<T>(`/campaigns/schema`, 'GET');
    },
    async getFilters<T = unknown>(): Promise<T> {
        return request<T>(`/campaigns/filters`, 'GET');
    },

    async uploadCampaigns<T = unknown>(file: File): Promise<T> {
        const formData = new FormData();
        formData.append('file', file);

        const token = localStorage.getItem('token');
        const headers: HeadersInit = {};
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        headers['X-CSRF-Token'] = 'v2-token-generation-pca';
        // Note: Content-Type is set automatically by fetch when using FormData

        const response = await fetch(`${API_URL}/campaigns/upload`, {
            method: 'POST',
            headers,
            body: formData,
        });

        if (!response.ok) {
            // Handle 401 Unauthorized
            if (response.status === 401 && typeof window !== 'undefined') {
                window.dispatchEvent(new CustomEvent('unauthorized'));
            }

            const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
            throw new Error(error.detail || 'Upload failed');
        }

        return response.json();
    },
    post: <T>(endpoint: string, body: unknown, options?: ApiRequestOptions) => request<T>(endpoint, 'POST', body, options),
    put: <T>(endpoint: string, body: unknown, options?: ApiRequestOptions) => request<T>(endpoint, 'PUT', body, options),
    delete: <T>(endpoint: string, options?: ApiRequestOptions) => request<T>(endpoint, 'DELETE', undefined, options),
    patch: <T>(endpoint: string, body: unknown, options?: ApiRequestOptions) => request<T>(endpoint, 'PATCH', body, options),
};
