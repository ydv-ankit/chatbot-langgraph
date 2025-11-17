import json
from typing import Annotated, Optional, TypedDict
from fastapi.responses import StreamingResponse
from langgraph.graph import StateGraph, add_messages, END
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch
from langchain_core.messages import AIMessageChunk, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from uuid import uuid4
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

# load environment variables
load_dotenv()

# initialize model and tools
llm = ChatOpenAI(model = "gpt-4o-mini")
search_tool = TavilySearch(max_results=4)
tools = [search_tool]
memory = MemorySaver()
llm_with_tools = llm.bind_tools(tools = tools)

# define state
class State(TypedDict):
    messages: Annotated[list, add_messages]

# define model
async def model(state: State):
    result = await llm_with_tools.ainvoke(state['messages'])
    return {
        "messages": [result]
    }

# define tools router
async def tools_router(state: State):
    last_message = state['messages'][-1]

    if (hasattr(last_message, "tool_calls") and len(last_message.tool_calls) > 0):
        return "tool_node"
    else:
        return END

    
# define tool node
async def tool_node(state: State):
    """Custom tool node that handles tool calls from LLM"""
    tool_calls = state["messages"][-1].tool_calls

    tool_messages = []

    # process each tool call
    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_id = tool_call["id"]

        if tool_name == "tavily_search":
            search_results = await search_tool.ainvoke(tool_args)
            tool_message = ToolMessage(
                content=str(search_results),
                tool_call_id = tool_id,
                name = tool_name
            )
            tool_messages.append(tool_message)
    
    return {
        "messages": tool_messages
    }

# build graph
graph_builder = StateGraph(State)
graph_builder.add_node("model", model)
graph_builder.add_node("tool_node", tool_node)
graph_builder.set_entry_point("model")

graph_builder.add_edge("tool_node", "model")
graph_builder.add_conditional_edges(
    "model",
    tools_router,
    {
        "tool_node": "tool_node",
        END: END
    }
)

graph = graph_builder.compile(checkpointer=memory)

# initialize FastAPI app
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

def serialize_ai_message(chunk):
    if isinstance(chunk, AIMessageChunk):
        return chunk.content
    raise TypeError(
        f"Object of type {type(chunk).__name__} is not a valid AIMessageChunk"
    )

async def generate_chat_stream(message: str, checkpoint_id: Optional[str] = None):
    is_new_thread = checkpoint_id is None
    if is_new_thread:
        checkpoint_id = uuid4()
        config = {
            "configurable": {
                "thread_id": checkpoint_id
            }
        }
        events = graph.astream_events({
            "messages": [HumanMessage(content=message)]
        }, config=config, version="v2")
        yield f"data: {{\"type\": \"checkpoint\", \"checkpoint_id\": \"{checkpoint_id}\"}}\n\n"
    else:
        config = {
            "configurable": {
                "thread_id": checkpoint_id
            }
        }
    async for event in graph.astream_events({
            "messages": [HumanMessage(content=message)]
        }, config=config, version="v2"):
        event_type = event['event']
        match event_type:
            case "on_chat_model_stream":
                chunk_content = serialize_ai_message(event['data']['chunk'])
                safe_content = chunk_content.replace("'", "\'")
                yield f"data: {{\"type\": \"content\", \"content\": \"{safe_content}\"}}\n\n"
            
            case "on_chat_model_end":
                output = event['data']['output']
                tool_calls = output.tool_calls if hasattr(output, 'tool_calls') and output.tool_calls else []
                search_calls = [call for call in tool_calls if call['name'] == "tavily_search"]
                if search_calls:
                    search_query = search_calls[0]['args'].get('query',"")
                    safe_query = search_query.replace('"', '\\"').replace("\n", "\\n")
                    yield f"data: {{\"type\": \"search_start\", \"query\": \"{safe_query}\"}}\n\n"
            
            case "on_tool_result":
                if event["name"] == "tavily_search":
                    output = event["data"]["output"]

                    # check if output is a list of results
                    if isinstance(output, list):
                        urls = []
                        for result in output:
                            if isinstance(result, dict) and 'url' in result:
                                urls.append(result['url'])
                        urls_json = json.dumps(urls)
                        yield f"data: {{\"type\": \"search_results\", \"urls\": \"{urls_json}\"}}\n\n"
        # yield f"data: {{\"type\": \"end\"}}\n\n"

# API endpoints
@app.get("/chat_stream/{message}")
async def stream_chat(message: str, checkpoint_id: Optional[str] = Query(default=None)):
    return StreamingResponse(
        generate_chat_stream(message, checkpoint_id),
        media_type="text/event-stream",
    )