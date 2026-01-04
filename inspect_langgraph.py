from src.agents.graph import agent_graph
import inspect

print(f"Type: {type(agent_graph)}")
print(f"Dir: {dir(agent_graph)}")
print(f"Has ainvoke: {hasattr(agent_graph, 'ainvoke')}")
print(f"Has invoke: {hasattr(agent_graph, 'invoke')}")
