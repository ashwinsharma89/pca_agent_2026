import json
from typing import Dict, Any, List
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.agents.state import AgentState
from src.query_engine.nl_to_sql import NaturalLanguageQueryEngine
from src.agents.enhanced_visualization_agent import EnhancedVisualizationAgent
from src.agents.b2b_specialist_agent import B2BSpecialistAgent
from src.config.settings import settings

# Initialize Tools/Agents
# Note: In a real app, these should be dependency-injected or lazily initialized
query_engine = NaturalLanguageQueryEngine(api_key=settings.openai_api_key)
viz_agent = EnhancedVisualizationAgent()
b2b_agent = B2BSpecialistAgent()

# --- Supervisor Node ---
async def supervisor_node(state: AgentState):
    """
    The orchestrator that decides which agent to call next.
    """
    messages = state["messages"]
    last_message = messages[-1] if messages else HumanMessage(content="")
    
    # Simple Router Logic using LLM
    llm = ChatOpenAI(model="gpt-4o", api_key=settings.openai_api_key)
    
    system_prompt = """You are a Supervisor managing a team of experts:
    1. 'Lead_Data_Analyst': Capable of running SQL queries on campaign data. Use for quantitative questions ("What is my ROAS?", "How much did we spend?").
    2. 'Visualization_Expert': Capable of generating charts. Use when the user asks for a graph, chart, or visual.
    3. 'B2B_Strategist': Capable of providing deep strategic analysis for B2B/LeadGen. Use for qualitative strategy or "Improvement" questions.
    
    Decide who to act next. 
    - If the user's request is fully answered or there is nothing left to do, return 'FINISH'.
    - If you need data first, call 'Lead_Data_Analyst'.
    - If you have data and need a chart, call 'Visualization_Expert'.
    - If you have data and need strategy, call 'B2B_Strategist'.
    
    Respond in JSON format: {"next": "AGENT_NAME", "reason": "why"}
    Example: {"next": "Lead_Data_Analyst", "reason": "Need to fetch spend data first"}
    """
    
    response = await llm.ainvoke([
        SystemMessage(content=system_prompt),
        *messages
    ])
    
    try:
        decision = json.loads(response.content.replace("```json", "").replace("```", ""))
        next_agent = decision.get("next", "FINISH")
    except:
        # Fallback
        next_agent = "FINISH"
        
    return {"next": next_agent}

# --- Worker Nodes ---

async def data_analyst_node(state: AgentState):
    """
    Wraps NaturalLanguageQueryEngine.
    """
    messages = state["messages"]
    last_user_msg = next((m for m in reversed(messages) if isinstance(m, HumanMessage)), None)
    query = last_user_msg.content if last_user_msg else ""
    
    try:
        # We assume 'user_id' is accessible via context or fixed for now
        # In a real app, pass this via state or config
        answer, sql, df = await query_engine.answer_question(query, user_id="system")
        
        # Store Data
        campaign_data = df.to_dict(orient="records") if not df.empty else []
        
        return {
            "messages": [AIMessage(content=f"Data Analyst: {answer}")],
            "campaign_data": {"active_dataset": campaign_data},
            "reports": [{"source": "Data Analyst", "sql": sql, "data_summary": answer}]
        }
    except Exception as e:
        return {
            "messages": [AIMessage(content=f"Data Analyst Error: {str(e)}")],
            "errors": [str(e)]
        }

async def visualizer_node(state: AgentState):
    """
    Wraps EnhancedVisualizationAgent.
    """
    campaign_data_dict = state.get("campaign_data") or {}
    data_context = campaign_data_dict.get("active_dataset", [])
    
    if not data_context:
        return {
            "messages": [AIMessage(content="Visualizer: I cannot draw a chart without data. Please ask the Data Analyst to fetch data first.")]
        }
        
    import pandas as pd
    df = pd.DataFrame(data_context)
    
    try:
        # Create dashboard viz
        viz_dict = viz_agent.create_dashboard_visualizations(df)
        
        # For this PoC, we just list the created charts
        chart_names = list(viz_dict.keys())
        msg = f"Visualizer: I have generated the following charts based on the data: {', '.join(chart_names)}."
        
        return {
            "messages": [AIMessage(content=msg)],
            "reports": [{"source": "Visualizer", "charts": chart_names}]
        }
    except Exception as e:
         return {
            "messages": [AIMessage(content=f"Visualizer Error: {str(e)}")],
            "errors": [str(e)]
        }

async def b2b_strategist_node(state: AgentState):
    """
    Wraps B2BSpecialistAgent.
    """
    data_context = state.get("campaign_data", {}).get("active_dataset", [])
    reports = state.get("reports", [])
    
    # Extract insights from previous reports
    base_insights = {"metrics": {}, "findings": []}
    for r in reports:
        if "data_summary" in r:
            base_insights["findings"].append(r["data_summary"])
            
    try:
        import pandas as pd
        df = pd.DataFrame(data_context) if data_context else None
        
        # Run enhancement
        enhanced = b2b_agent.enhance_analysis(base_insights, campaign_data=df)
        
        recommendations = enhanced.get("recommendations", [])
        rec_text = "\n".join([f"- {r.get('recommendation')}" for r in recommendations])
        
        msg = f"B2B Strategist: Based on the analysis, here are my strategic recommendations:\n{rec_text}"
        
        return {
            "messages": [AIMessage(content=msg)],
            "reports": [{"source": "B2B Strategist", "strategy": enhanced}]
        }
    except Exception as e:
        return {
            "messages": [AIMessage(content=f"B2B Strategist Error: {str(e)}")],
            "errors": [str(e)]
        }
