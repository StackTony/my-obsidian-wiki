LangGraph’s **subgraph** feature is a game-changer for building complex AI workflows. It helps break down large workflows into smaller, modular components, making them more manageable, reusable, and maintainable. If you're looking to improve the structure of your AI applications, understanding when and how to use subgraphs is essential.

Let’s dive into why subgraphs matter and how to integrate them into your LangGraph projects.

[![ ](https://media2.dev.to/dynamic/image/width=800%2Cheight=%2Cfit=scale-down%2Cgravity=auto%2Cformat=auto/https%3A%2F%2Fdev-to-uploads.s3.amazonaws.com%2Fuploads%2Farticles%2Fr6l8llftu27a6ns66fz3.png)](https://media2.dev.to/dynamic/image/width=800%2Cheight=%2Cfit=scale-down%2Cgravity=auto%2Cformat=auto/https%3A%2F%2Fdev-to-uploads.s3.amazonaws.com%2Fuploads%2Farticles%2Fr6l8llftu27a6ns66fz3.png)

## When Should You Use Subgraphs?

Subgraphs shine in the following scenarios:

**Multi-Agent Systems** – When multiple agents need to collaborate, subgraphs help organize logic for each agent or team.

**Code Reusability** – Have a set of nodes you frequently use? Define them as a subgraph for seamless integration across multiple workflows.

**Independent Development** – Different teams can work on separate subgraphs, allowing for independent development and testing.

**Managing Complexity** – For intricate AI workflows, breaking them into subgraphs keeps your architecture clean and modular.

## How to Add Subgraphs to Your LangGraph Project

There are two primary ways to integrate subgraphs into a parent graph:

### 1️⃣ Adding a Compiled Subgraph as a Node\*\*

Best when the parent graph and subgraph share state keys and don’t require state transformation.

[![ ](https://media2.dev.to/dynamic/image/width=800%2Cheight=%2Cfit=scale-down%2Cgravity=auto%2Cformat=auto/https%3A%2F%2Fdev-to-uploads.s3.amazonaws.com%2Fuploads%2Farticles%2Fk444oehvfb7xkniv9xp3.png)](https://media2.dev.to/dynamic/image/width=800%2Cheight=%2Cfit=scale-down%2Cgravity=auto%2Cformat=auto/https%3A%2F%2Fdev-to-uploads.s3.amazonaws.com%2Fuploads%2Farticles%2Fk444oehvfb7xkniv9xp3.png)

[![ ](https://media2.dev.to/dynamic/image/width=800%2Cheight=%2Cfit=scale-down%2Cgravity=auto%2Cformat=auto/https%3A%2F%2Fdev-to-uploads.s3.amazonaws.com%2Fuploads%2Farticles%2Ftdtvorlvvqorgynlc3zl.png)](https://media2.dev.to/dynamic/image/width=800%2Cheight=%2Cfit=scale-down%2Cgravity=auto%2Cformat=auto/https%3A%2F%2Fdev-to-uploads.s3.amazonaws.com%2Fuploads%2Farticles%2Ftdtvorlvvqorgynlc3zl.png)

```
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict
from langchain_community.tools.tavily_search import TavilySearchResults
import os
from dotenv import load_dotenv

# Ensure you have set your Tavily API key as an environment variable
load_dotenv()

# Define subgraph
class SubgraphState(TypedDict):
    query: str
    search_results: str

def tavily_search(state: SubgraphState):
    search = TavilySearchResults(max_results=3)  # I am setting my search result return 3 results
    results = search.invoke(state["query"])
    return {"search_results": results}

def process_results(state: SubgraphState):
    search_results = state["search_results"]
    processed_result = ""

    if isinstance(search_results, list):
        for result in search_results:
            url = result.get("url", "No URL")
            content = result.get("content", "No Content")
            processed_result += f"URL: {url}\nContent: {content}\n\n"  #Added the url to the process result
    else:
        processed_result = "No search results found."

    return {"query": state["query"] + " - " + processed_result}

subgraph = StateGraph(SubgraphState)
subgraph.add_node("search", tavily_search)
subgraph.add_node("process", process_results)
subgraph.add_edge(START, "search")
subgraph.add_edge("search", "process")

subgraph = subgraph.compile()
image = subgraph.get_graph().draw_ascii()
print(image)
image1 =subgraph.get_graph().draw_png()

with open("sreeni_subgraph.png","wb") as file:
    file.write(image1)

# Define parent graph
class ParentState(TypedDict):
    query: str

def node_1(state: ParentState):
    return {"query": "Searching for: " + state["query"]}

builder = StateGraph(ParentState)
builder.add_node("node_1", node_1)
builder.add_node("subgraph", subgraph)  # Add the compiled subgraph as a node
builder.add_edge(START, "node_1")
builder.add_edge("node_1", "subgraph")
builder.add_edge("subgraph", END)

graph = builder.compile()

image = graph.get_graph().draw_ascii()
print(image)
image1 =graph.get_graph().draw_png()

with open("sreeni_Main_and_subgraph.png","wb") as file:
    file.write(image1)

# Run the graph
result= graph.invoke({"query": "NVIDA"}, subgraphs=True)
print(result)
```

## What Does the above Code Do?

The core of the code revolves around LangGraph's StateGraph framework, which is used to model and execute workflows. The workflow here involves two key steps:

Tavily Search: The subgraph takes a user-provided query and makes a request to the Tavily API for search results (limited to 3 results). Each result contains a URL and content. These results are then formatted into a readable string.

Processing Results: The processed search results are returned and combined with the original query, providing a clear output for the user.

The main graph consists of a simple node that modifies the input query and passes it to the subgraph, which handles the search and result formatting. The results are then returned as the output, showing both the search query and the formatted search results.

## Visualizing the Workflow

Once the workflow is defined, the code compiles it into a graph and visualizes it in two formats: ASCII and PNG. These visuals give us a clear view of the flow from the start node, through the subgraph, to the final result. The images are saved as sreeni\_subgraph.png and sreeni\_Main\_and\_subgraph.png, providing a useful representation of the process for documentation or debugging purposes.

## Running the Graph

Finally, the graph is executed with an example query ("NVIDIA"). The result is printed, showing the combined query and processed search results. This demonstrates how LangGraph can handle dynamic inputs and return structured outputs, all while maintaining clear visibility into the process through the generated graphs.

This workflow illustrates just one of the many ways LangGraph can be used to create organized, visual, and easy-to-debug workflows that interact with external APIs and process data in a structured manner.

### 2️⃣ Using a Node Function to Invoke the Subgraph\*\*

Ideal when the parent graph and subgraph have different state schemas, requiring state transformation.

```
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict
from langchain_community.tools.tavily_search import TavilySearchResults
import os
from dotenv import load_dotenv
load_dotenv()

# Ensure you have set your Tavily API key as an environment variable

# Define subgraph
class SubgraphState(TypedDict):
    query: str
    search_results: str

def tavily_search(state: SubgraphState):
    search = TavilySearchResults(max_results=1)
    results = search.invoke(state["query"])
    return {"search_results": results}

def process_results(state: SubgraphState):
    search_results = state["search_results"]
    processed_result = ""

    if isinstance(search_results, list):
        for result in search_results:
            url = result.get("url", "No URL")
            content = result.get("content", "No Content")

            processed_result += f"URL: {url}\nContent: {content}...\n\n"  #Added the url to the process result
    else:
        processed_result = "No search results found."

    return {"query": state["query"] + " - " + processed_result}

subgraph = StateGraph(SubgraphState)
subgraph.add_node("search", tavily_search)
subgraph.add_node("process", process_results)
subgraph.add_edge(START, "search")
subgraph.add_edge("search", "process")

subgraph = subgraph.compile()

# Define parent graph
class ParentState(TypedDict):
    query: str

def node_1(state: ParentState):
    return {"query": "Searching for: " + state["query"]}

def node_2(state: ParentState):
    # transform the state to the subgraph state
    response = subgraph.invoke({"query": state["query"]})
    # transform response back to the parent state
    return {"search_results": response["search_results"]}

builder = StateGraph(ParentState)
builder.add_node("node_1", node_1)
builder.add_node("subgraph", subgraph)  # Add the compiled subgraph as a node
builder.add_edge(START, "node_1")
builder.add_edge("node_1", "subgraph")
builder.add_edge("subgraph", END)

graph = builder.compile()

image = graph.get_graph().draw_ascii()
print(image)
image1 =graph.get_graph().draw_png()

with open("sreeni_Main_and_subgraph_as_node.png","wb") as file:
    file.write(image1)
# Run the graph
result= graph.invoke({"query": "NVIDA"}, subgraphs=True)
print(result)
```

## Best Practices for Using Subgraphs

**Shared State Keys** – Ensure the parent graph and subgraph share at least one state key for smooth communication.

**State Transformation** – When state structures differ, use a node function to manage the transformation.

**Modular Design** – Think modular! Reusable subgraphs keep your workflows efficient and scalable.

**Clear Interfaces** – Define precise input and output schemas to ensure seamless integration with parent graphs.

By leveraging **subgraphs** in LangGraph, you can build AI systems that are more **scalable, organized, and flexible**. Whether you’re constructing multi-agent workflows or breaking down complex processes, subgraphs offer a structured approach to handling AI workflow challenges.

**Thanks  
Sreeni Ramadorai**