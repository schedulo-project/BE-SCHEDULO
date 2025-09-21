import json
from typing import Annotated, Optional, Any
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain.schema import HumanMessage, AIMessage

from .core_agent import run_core_agent
from .render_agent import generate_html
from .templates import render_template
from jinja2 import Environment, FileSystemLoader


# ----------------------------
# 상태 정의
# ----------------------------
class State(TypedDict):
    user_id: int
    query: str
    messages: Annotated[list, add_messages]
    data: Optional[Any]
    render_html: bool
    html: Optional[str]
    template_name: Optional[str]


# ----------------------------
# Core Agent 노드
# ----------------------------
def core_agent(state: State) -> State:
    # Core Agent 실행
    core_response = run_core_agent(state["query"], state["user_id"])
    print(core_response)

    # 메시지 누적
    state["messages"] = [AIMessage(content=core_response.get("message", ""))]
    state["data"] = core_response.get("data")
    state["render_html"] = core_response.get("render_html", False)

    # core_agent가 템플릿 이름까지 결정하도록 (없으면 None)
    state["template_name"] = core_response.get("template_name", None)

    return state


# ----------------------------
# Render Agent 노드
# ----------------------------
def render_agent(state: State) -> State:
    html_response = generate_html(state["query"], state["data"], state["template_name"])
    print(html_response)
    state["html"] = html_response

    return state


# ----------------------------
# StateGraph 구성
# ----------------------------
graph = StateGraph(State)

# 노드 추가
graph.add_node("core", core_agent)
graph.add_node("render", render_agent)

# 시작 노드
graph.add_edge(START, "core")

# Core → Render / END 조건부 엣지
def decide_next(state: State):
    if state.get("render_html") and state.get("data") is not None:
        return "render"
    return END


graph.add_conditional_edges("core", decide_next)

# Render → END
graph.add_edge("render", END)

compiled_graph = graph.compile()


# ----------------------------
# 실행 함수
# ----------------------------
def run_agent_graph(query: str, user_id: int) -> State:

    # 초기 상태
    initial_state: State = {
        "user_id": user_id,
        "query": query,
        "messages": [],
        "data": None,
        "render_html": False,
        "html": None,
        "template_name": None,
    }

    return compiled_graph.invoke(initial_state)
