
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

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

interface DashboardFilters {
    platforms: string[];
    dateRange?: { from: Date; to: Date };
    channels: string[];
    funnelStages: string[];
    devices: string[];
    placements: string[];
    regions: string[];
    adTypes: string[];
}

interface DimensionFilters {
    selectedDevice: string | null;
    selectedRegion: string | null;
    selectedAudience: string | null;
    selectedAge: string | null;
    selectedAdType: string | null;
    selectedObjective: string | null;
    selectedTargeting: string | null;
    selectedFunnelStage: string | null;
}

export const useDashboardVisualizations = (
    filters: DashboardFilters,
    sourceFilter: string,
    dimensions: DimensionFilters
) => {
    return useQuery({
        queryKey: ['dashboard-visualizations', filters, sourceFilter, dimensions],
        queryFn: async () => {
            const filterParams: any = {};

            // Use global filters for all API calls
            if (filters.platforms.length > 0) {
                filterParams.platforms = filters.platforms.join(',');
            } else if (sourceFilter && sourceFilter !== 'all') {
                filterParams.platforms = sourceFilter;
            }

            if (filters.dateRange?.from) {
                filterParams.startDate = filters.dateRange.from.toISOString().split('T')[0];
            }
            if (filters.dateRange?.to) {
                filterParams.endDate = filters.dateRange.to.toISOString().split('T')[0];
            }

            if (filters.channels.length > 0) filterParams.channels = filters.channels.join(',');
            if (filters.funnelStages.length > 0) filterParams.funnelStages = filters.funnelStages.join(',');
            if (filters.devices.length > 0) filterParams.devices = filters.devices.join(',');
            if (filters.placements.length > 0) filterParams.placements = filters.placements.join(',');
            if (filters.regions.length > 0) filterParams.regions = filters.regions.join(',');
            if (filters.adTypes.length > 0) filterParams.adTypes = filters.adTypes.join(',');

            // Dimension Linking
            if (dimensions.selectedDevice) filterParams.devices = filterParams.devices ? `${filterParams.devices},${dimensions.selectedDevice}` : dimensions.selectedDevice;
            if (dimensions.selectedRegion) filterParams.regions = filterParams.regions ? `${filterParams.regions},${dimensions.selectedRegion}` : dimensions.selectedRegion;
            if (dimensions.selectedAudience) filterParams.audiences = dimensions.selectedAudience;
            if (dimensions.selectedAge) filterParams.ages = dimensions.selectedAge;
            if (dimensions.selectedAdType) filterParams.adTypes = filterParams.adTypes ? `${filterParams.adTypes},${dimensions.selectedAdType}` : dimensions.selectedAdType;
            if (dimensions.selectedObjective) filterParams.objectives = dimensions.selectedObjective;
            if (dimensions.selectedTargeting) filterParams.targetings = dimensions.selectedTargeting;
            if (dimensions.selectedFunnelStage) filterParams.funnelStages = filterParams.funnelStages ? `${filterParams.funnelStages},${dimensions.selectedFunnelStage}` : dimensions.selectedFunnelStage;

            const visualizations = await api.getGlobalVisualizations<VisualizationsData>(filterParams);
            return visualizations;
        }
    });
};

export const useDashboardStats = (
    filters: DashboardFilters,
    sourceFilter: string,
    dimensions: DimensionFilters
) => {
    return useQuery({
        queryKey: ['dashboard-stats', filters, sourceFilter, dimensions],
        queryFn: async () => {
            const filterParams: any = {};

            // Use global filters for all API calls
            if (filters.platforms.length > 0) {
                filterParams.platforms = filters.platforms.join(',');
            } else if (sourceFilter && sourceFilter !== 'all') {
                filterParams.platforms = sourceFilter;
            }

            if (filters.dateRange?.from) {
                filterParams.startDate = filters.dateRange.from.toISOString().split('T')[0];
            }
            if (filters.dateRange?.to) {
                filterParams.endDate = filters.dateRange.to.toISOString().split('T')[0];
            }

            if (filters.channels.length > 0) filterParams.channels = filters.channels.join(',');
            if (filters.funnelStages.length > 0) filterParams.funnelStages = filters.funnelStages.join(',');
            if (filters.devices.length > 0) filterParams.devices = filters.devices.join(',');
            if (filters.placements.length > 0) filterParams.placements = filters.placements.join(',');
            if (filters.regions.length > 0) filterParams.regions = filters.regions.join(',');
            if (filters.adTypes.length > 0) filterParams.adTypes = filters.adTypes.join(',');

            // Dimension Linking
            if (dimensions.selectedDevice) filterParams.devices = filterParams.devices ? `${filterParams.devices},${dimensions.selectedDevice}` : dimensions.selectedDevice;
            if (dimensions.selectedRegion) filterParams.regions = filterParams.regions ? `${filterParams.regions},${dimensions.selectedRegion}` : dimensions.selectedRegion;
            if (dimensions.selectedAudience) filterParams.audiences = dimensions.selectedAudience;
            if (dimensions.selectedAge) filterParams.ages = dimensions.selectedAge;
            if (dimensions.selectedAdType) filterParams.adTypes = filterParams.adTypes ? `${filterParams.adTypes},${dimensions.selectedAdType}` : dimensions.selectedAdType;
            if (dimensions.selectedObjective) filterParams.objectives = dimensions.selectedObjective;
            if (dimensions.selectedTargeting) filterParams.targetings = dimensions.selectedTargeting;
            if (dimensions.selectedFunnelStage) filterParams.funnelStages = filterParams.funnelStages ? `${filterParams.funnelStages},${dimensions.selectedFunnelStage}` : dimensions.selectedFunnelStage;


            const statsParams = new URLSearchParams();
            if (filterParams.startDate) statsParams.append('start_date', filterParams.startDate);
            if (filterParams.endDate) statsParams.append('end_date', filterParams.endDate);
            if (filterParams.platforms) statsParams.append('platforms', filterParams.platforms);
            if (filterParams.channels) statsParams.append('channels', filterParams.channels);
            if (filterParams.regions) statsParams.append('regions', filterParams.regions);
            if (filterParams.devices) statsParams.append('devices', filterParams.devices);
            if (filterParams.placements) statsParams.append('placements', filterParams.placements);
            if (filterParams.adTypes) statsParams.append('adTypes', filterParams.adTypes);
            if (filterParams.funnelStages) statsParams.append('funnelStages', filterParams.funnelStages);

            if (filterParams.audiences) statsParams.append('audiences', filterParams.audiences);
            if (filterParams.ages) statsParams.append('ages', filterParams.ages);
            if (filterParams.objectives) statsParams.append('objectives', filterParams.objectives);
            if (filterParams.targetings) statsParams.append('targetings', filterParams.targetings);

            const stats = await api.get(`/campaigns/dashboard-stats?${statsParams.toString()}`);
            return stats;
        }
    });
};
