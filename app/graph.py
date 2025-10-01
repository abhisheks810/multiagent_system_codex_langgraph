from typing import TypedDict
from langgraph.graph import StateGraph, END

from app.nodes.plan import node_plan
from app.nodes.uiux import node_uiux
from app.nodes.tester import node_tester
from app.nodes.qa_geo import node_qa_geo
from app.nodes.integrate import node_integrate
from app.nodes.product_manager import node_product_manager
from app.nodes.open_mr import node_open_mr

class AppState(TypedDict, total=False):
    feature: str
    plan: str
    uiux: str
    tester: str
    qa_geo: str
    integration_report: str
    project_status_path: str
    project_status_preview: str
    mr: str

def build_graph():
    g = StateGraph(AppState)

    # Nodes
    g.add_node("plan", node_plan)
    g.add_node("uiux", node_uiux)
    g.add_node("tester", node_tester)
    g.add_node("qa_geo", node_qa_geo)
    g.add_node("integrate", node_integrate)
    g.add_node("product_manager", node_product_manager)
    g.add_node("open_mr", node_open_mr)

    # Entry
    g.set_entry_point("plan")

    # Parallel after plan
    g.add_edge("plan", "uiux")
    g.add_edge("plan", "tester")
    g.add_edge("plan", "qa_geo")

    # Route to integrate (idempotent)
    g.add_edge("uiux", "integrate")
    g.add_edge("tester", "integrate")
    g.add_edge("qa_geo", "integrate")

    # integrate → product_manager → open_mr → END
    g.add_edge("integrate", "product_manager")
    g.add_edge("product_manager", "open_mr")
    g.add_edge("open_mr", END)

    return g.compile()
