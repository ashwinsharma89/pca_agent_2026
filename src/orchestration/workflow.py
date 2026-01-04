"""
LangGraph orchestration workflow for PCA Agent.
Coordinates all agents in the analysis pipeline.
"""
from typing import TypedDict, Annotated, Sequence
import operator
from datetime import datetime

from langgraph.graph import StateGraph, END
from loguru import logger

from ..models import Campaign, CampaignStatus, ConsolidatedReport, ChannelPerformance, ReportConfig
from ..agents import (
    VisionAgent,
    ExtractionAgent,
    ReasoningAgent,
    VisualizationAgent
)


class WorkflowState(TypedDict):
    """State for the workflow graph."""
    campaign: Campaign
    channel_performances: list[ChannelPerformance]
    visualizations: list[dict]
    report_path: str
    errors: Annotated[Sequence[str], operator.add]
    logs: Annotated[Sequence[str], operator.add]


class PCAWorkflow:
    """Orchestrates the entire PCA analysis workflow using LangGraph."""
    
    def __init__(self):
        """Initialize the workflow with all agents."""
        self.vision_agent = VisionAgent()
        self.extraction_agent = ExtractionAgent()
        self.reasoning_agent = ReasoningAgent()
        self.visualization_agent = VisualizationAgent()
        # Note: Report generation removed - use external reporting tools
        
        # Build the graph
        self.graph = self._build_graph()
        logger.info("PCA Workflow initialized")
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(WorkflowState)
        
        # Add nodes
        workflow.add_node("vision_extraction", self.vision_extraction_node)
        workflow.add_node("data_normalization", self.data_normalization_node)
        workflow.add_node("reasoning_analysis", self.reasoning_analysis_node)
        workflow.add_node("visualization_generation", self.visualization_generation_node)
        workflow.add_node("report_assembly", self.report_assembly_node)
        
        # Define edges
        workflow.set_entry_point("vision_extraction")
        workflow.add_edge("vision_extraction", "data_normalization")
        workflow.add_edge("data_normalization", "reasoning_analysis")
        workflow.add_edge("reasoning_analysis", "visualization_generation")
        workflow.add_edge("visualization_generation", "report_assembly")
        workflow.add_edge("report_assembly", END)
        
        return workflow.compile()
    
    async def run(self, campaign: Campaign, config: ReportConfig = None) -> ConsolidatedReport:
        """
        Run the complete workflow.
        
        Args:
            campaign: Campaign with uploaded snapshots
            config: Report configuration
            
        Returns:
            Consolidated report with generated report path
        """
        logger.info(f"Starting workflow for campaign {campaign.campaign_id}")
        campaign.status = CampaignStatus.PROCESSING
        
        # Initialize state
        initial_state = WorkflowState(
            campaign=campaign,
            channel_performances=[],
            visualizations=[],
            report_path="",
            errors=[],
            logs=[]
        )
        
        try:
            # Run the graph
            final_state = await self.graph.ainvoke(initial_state)
            
            # Build consolidated report
            consolidated_report = ConsolidatedReport(
                campaign=final_state["campaign"],
                executive_summary=self._generate_executive_summary(final_state),
                total_spend=sum(cp.total_spend or 0 for cp in final_state["channel_performances"]),
                total_conversions=sum(cp.total_conversions or 0 for cp in final_state["channel_performances"]),
                overall_roas=self._calculate_overall_roas(final_state["channel_performances"]),
                channel_performances=final_state["channel_performances"],
                cross_channel_insights=final_state["campaign"].insights.get("cross_channel_insights", []) if final_state["campaign"].insights else [],
                achievements=final_state["campaign"].achievements or [],
                recommendations=final_state["campaign"].recommendations or [],
                visualizations=final_state["visualizations"]
            )
            
            # Update campaign
            campaign.status = CampaignStatus.COMPLETED
            campaign.report_path = final_state["report_path"]
            campaign.report_generated_at = datetime.utcnow()
            campaign.processing_logs.extend(final_state["logs"])
            
            logger.info(f"Workflow completed successfully for campaign {campaign.campaign_id}")
            return consolidated_report
            
        except Exception as e:
            logger.error(f"Workflow failed: {e}")
            campaign.status = CampaignStatus.FAILED
            campaign.processing_error = str(e)
            raise
    
    async def vision_extraction_node(self, state: WorkflowState) -> WorkflowState:
        """Node: Extract data from dashboard snapshots using Vision Agent."""
        logger.info("Starting vision extraction")
        campaign = state["campaign"]
        campaign.status = CampaignStatus.EXTRACTING
        
        logs = []
        errors = []
        
        for snapshot in campaign.snapshots:
            try:
                logger.info(f"Processing snapshot {snapshot.snapshot_id}")
                updated_snapshot = await self.vision_agent.analyze_snapshot(snapshot)
                
                # Update snapshot in campaign
                for i, s in enumerate(campaign.snapshots):
                    if s.snapshot_id == snapshot.snapshot_id:
                        campaign.snapshots[i] = updated_snapshot
                        break
                
                logs.append(f"Extracted data from {snapshot.platform.value} snapshot")
                
            except Exception as e:
                error_msg = f"Failed to process snapshot {snapshot.snapshot_id}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        return {
            **state,
            "campaign": campaign,
            "logs": logs,
            "errors": errors
        }
    
    async def data_normalization_node(self, state: WorkflowState) -> WorkflowState:
        """Node: Normalize and validate extracted data."""
        logger.info("Starting data normalization")
        campaign = state["campaign"]
        
        # Normalize metrics
        campaign = self.extraction_agent.normalize_campaign_data(campaign)
        
        # Calculate derived metrics
        derived_metrics = self.extraction_agent.calculate_derived_metrics(campaign.normalized_metrics)
        campaign.normalized_metrics.extend(derived_metrics)
        
        logs = [f"Normalized {len(campaign.normalized_metrics)} metrics"]
        
        return {
            **state,
            "campaign": campaign,
            "logs": logs
        }
    
    async def reasoning_analysis_node(self, state: WorkflowState) -> WorkflowState:
        """Node: Perform agentic reasoning and generate insights."""
        logger.info("Starting reasoning analysis")
        campaign = state["campaign"]
        campaign.status = CampaignStatus.REASONING
        
        # Analyze campaign
        campaign = await self.reasoning_agent.analyze_campaign(campaign)
        
        # Extract channel performances from insights
        channel_performances = []
        if campaign.insights and "channel_performances" in campaign.insights:
            for cp_dict in campaign.insights["channel_performances"]:
                channel_performances.append(ChannelPerformance(**cp_dict))
        
        logs = [
            f"Generated insights for {len(channel_performances)} channels",
            f"Detected {len(campaign.achievements or [])} achievements",
            f"Generated {len(campaign.recommendations or [])} recommendations"
        ]
        
        return {
            **state,
            "campaign": campaign,
            "channel_performances": channel_performances,
            "logs": logs
        }
    
    async def visualization_generation_node(self, state: WorkflowState) -> WorkflowState:
        """Node: Generate visualizations."""
        logger.info("Starting visualization generation")
        campaign = state["campaign"]
        channel_performances = state["channel_performances"]
        
        visualizations = self.visualization_agent.generate_all_visualizations(
            campaign,
            channel_performances
        )
        
        logs = [f"Generated {len(visualizations)} visualizations"]
        
        return {
            **state,
            "visualizations": visualizations,
            "logs": logs
        }
    
    async def report_assembly_node(self, state: WorkflowState) -> WorkflowState:
        """Node: Assemble and generate final report."""
        logger.info("Starting report assembly")
        campaign = state["campaign"]
        campaign.status = CampaignStatus.GENERATING_REPORT
        
        # Build consolidated report
        consolidated_report = ConsolidatedReport(
            campaign=campaign,
            executive_summary=self._generate_executive_summary(state),
            total_spend=sum(cp.total_spend or 0 for cp in state["channel_performances"]),
            total_conversions=sum(cp.total_conversions or 0 for cp in state["channel_performances"]),
            overall_roas=self._calculate_overall_roas(state["channel_performances"]),
            channel_performances=state["channel_performances"],
            cross_channel_insights=[],  # Will be populated from campaign.insights
            achievements=campaign.achievements or [],
            recommendations=campaign.recommendations or [],
            visualizations=state["visualizations"]
        )
        
        # Generate report (simplified - just return path)
        report_path = f"reports/{campaign.campaign_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        logs = [f"Report generated: {report_path}"]
        
        return {
            **state,
            "report_path": report_path,
            "logs": logs
        }
    
    def _generate_executive_summary(self, state: WorkflowState) -> str:
        """Generate executive summary from state."""
        campaign = state["campaign"]
        channel_performances = state["channel_performances"]
        
        total_spend = sum(cp.total_spend or 0 for cp in channel_performances)
        total_conversions = sum(cp.total_conversions or 0 for cp in channel_performances)
        
        summary = f"""
This report analyzes the performance of {campaign.campaign_name} across {len(channel_performances)} advertising channels 
from {campaign.date_range.start} to {campaign.date_range.end}.

The campaign invested ${total_spend:,.2f} and generated {total_conversions:,.0f} conversions. 
Analysis reveals key insights across channel performance, cross-channel synergies, and optimization opportunities.
        """.strip()
        
        return summary
    
    def _calculate_overall_roas(self, channel_performances: list[ChannelPerformance]) -> float:
        """Calculate overall ROAS across all channels."""
        total_spend = sum(cp.total_spend or 0 for cp in channel_performances)
        total_conversions = sum(cp.total_conversions or 0 for cp in channel_performances)
        
        if total_spend > 0 and total_conversions > 0:
            # Assuming average order value of $100 for ROAS calculation
            # In production, this should come from actual revenue data
            revenue = total_conversions * 100
            return revenue / total_spend
        
        return 0.0
