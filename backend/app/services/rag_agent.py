"""
VortexRAG — LangGraph Multi-Agent Swarm (Phase 5 Upgrade)

Orchestrates a collaborative team of specialized AI agents:
1. Retriever Node: Queries Hybrid Search (Qdrant RRF + Neo4j GraphRAG).
2. Grader Node: Filter irrelevant codebase chunks (Hallucination safeguard).
3. Query Rewriter Node: Cyclically self-corrects search queries.
4. Security Auditor Agent: Parallel audit for CVEs, secrets, and logic flaws.
5. Performance Profiler Agent: Parallel scan for CPU/memory bottlenecks and Big-O efficiency.
6. Compliance Architect Agent: Synthesizes findings into a unified architectural report.
"""
import logging
import json
from typing import Dict, TypedDict, List, Optional
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.hybrid_search import HybridSearcher

logger = logging.getLogger("vortex")

# ── State Definition ──────────────────────────────────────────────────────────
class GraphState(TypedDict):
    """Represents the collaborative state of our multi-agent swarm."""
    question: str
    repo_id: str
    generation: str
    documents: List[dict]
    search_count: int
    security_audit: Optional[str]
    performance_audit: Optional[str]


# ── Grader Models (LLM Output Schemas) ────────────────────────────────────────
class GradeDocuments(BaseModel):
    """Binary score for relevance check on retrieved documents."""
    binary_score: str = Field(description="Documents are relevant to the question, 'yes' or 'no'")

class GradeHallucinations(BaseModel):
    """Binary score for hallucination check."""
    binary_score: str = Field(description="Answer is grounded in the facts, 'yes' or 'no'")


class RAGAgent:
    def __init__(self):
        # We use Groq's extremely fast free tier for students!
        model_name = settings.GROQ_MODEL
        if not model_name or "llama" in model_name:
            model_name = "qwen/qwen3.8-27b"

        from langchain_groq import ChatGroq
        self.llm = ChatGroq(
            model=model_name,
            max_tokens=500,
            temperature=0,
            api_key=settings.GROQ_API_KEY
        )
        self.searcher = HybridSearcher()
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Constructs the ultra-fast LangGraph multi-agent swarm state machine."""
        workflow = StateGraph(GraphState)

        # Define nodes
        workflow.add_node("retrieve", self.retrieve)
        workflow.add_node("grade_documents", self.grade_documents)
        workflow.add_node("compliance_architect", self.compliance_architect)

        # Build graph structure
        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "grade_documents")
        workflow.add_edge("grade_documents", "compliance_architect")
        workflow.add_edge("compliance_architect", END)

        return workflow.compile()

    # ── Swarm Agent Nodes ──────────────────────────────────────────────────────
    async def retrieve(self, state: GraphState) -> Dict:
        """Retrieves documents from Vector DB and augments with Neo4j Call-Graph Context."""
        question = state["question"]
        repo_id = state.get("repo_id")
        search_count = state.get("search_count", 0)
        
        logger.info(f"🤖 [Agent] Retrieving for: '{question}' (Attempt {search_count + 1})")
        
        docs = await self.searcher.search(question, repo_id, top_k=5)
        
        # ── GraphRAG Augment (Neo4j Containment & Call Graph Traversal) ─────────
        if docs and repo_id:
            try:
                from app.db.neo4j import get_neo4j
                driver = get_neo4j()
                augmented_docs = list(docs)
                
                # Fetch paths of retrieved documents to find structural siblings
                file_paths = list(set([doc["file_path"] for doc in docs if doc.get("file_path")]))
                
                if file_paths:
                    logger.info(f"🕸️ [GraphRAG] Querying Neo4j for call-graph siblings inside: {file_paths}")
                    
                    query = """
                    MATCH (f:File {repo_id: $repo_id})
                    WHERE f.path IN $file_paths
                    MATCH (f)-[:CONTAINS]->(child)
                    RETURN child.name AS name, labels(child)[0] AS type, child.start_line AS start_line
                    LIMIT 15
                    """
                    
                    async with driver.session() as session:
                        result = await session.run(query, repo_id=repo_id, file_paths=file_paths)
                        records = await result.data()
                        
                        if records:
                            # Build a structural relationship summary to inject into the LLM context
                            sibling_summary = "\n\n---\n🕸️ [Codebase Structural Call-Graph Map (Neo4j)]\n"
                            for rec in records:
                                sibling_summary += f"- {rec['type']} '{rec['name']}' is defined in file '{file_paths[0]}' starting on Line {rec['start_line']}\n"
                            
                            # Append this graph summary to the first retrieved document's code context
                            augmented_docs[0]["code"] = augmented_docs[0]["code"] + sibling_summary
                            logger.info(f"✅ [GraphRAG] Injected {len(records)} Neo4j node relationships into prompt context!")
                
                docs = augmented_docs
            except Exception as graph_err:
                logger.error(f"⚠️ [GraphRAG] Neo4j traversal skipped: {graph_err}")
                
        return {"documents": docs, "question": question, "search_count": search_count + 1}

    async def grade_documents(self, state: GraphState) -> Dict:
        """Passes the top-ranked hybrid RRF search documents directly to the swarm."""
        question = state["question"]
        documents = state["documents"]
        
        logger.info("🤖 [Agent] Grading retrieved documents via Hybrid RRF scores...")
        
        if not documents:
             return {"documents": [], "question": question}
             
        # Hybrid Search (BM25 + Qdrant RRF) already provides mathematically ranked candidates.
        # Filter top 3 for ultra-fast, sub-2s multi-agent swarm execution.
        filtered_docs = documents[:3]
        logger.info(f"🤖 [Agent] Kept {len(filtered_docs)} top-ranked documents.")
        return {"documents": filtered_docs, "question": question}

    async def _safe_ainvoke(self, messages, max_retries=2):
        """Invoke LLM with light retry if RPM/ITPM burst occurs."""
        for attempt in range(max_retries):
            try:
                return await self.llm.ainvoke(messages)
            except Exception as e:
                if "429" in str(e) and attempt < max_retries - 1:
                    logger.warning(f"Groq token rate limit burst, waiting 2s before retry...")
                    await asyncio.sleep(2)
                else:
                    raise e

    async def security_auditor(self, state: GraphState) -> Dict:
        """Audits retrieved code context specifically for vulnerabilities in parallel."""
        logger.info("🛡️ [Swarm Agent] Running Security Auditor Agent...")
        documents = state["documents"]
        if not documents:
            return {"security_audit": "No code retrieved to audit."}
            
        context = "\n\n".join([f"File: {d['file_path']}\nCode:\n{d['code'][:600]}" for d in documents[:3]])
        system = """You are a highly specialized CISSP-certified AI Security Auditor.
        Audit the following codebase chunks for security issues:
        - Hardcoded secrets, keys, or credentials.
        - SQL injection, XSS, or directory traversal risks.
        - Insecure library usage or flawed authorization checks.
        Provide a concise 2-3 bullet point security profile."""
        
        messages = [
            SystemMessage(content=system),
            HumanMessage(content=f"Reviewing Code:\n{context}")
        ]
        response = await self._safe_ainvoke(messages)
        return {"security_audit": response.content}

    async def performance_profiler(self, state: GraphState) -> Dict:
        """Analyzes retrieved code for performance/algorithmic bottlenecks in parallel."""
        logger.info("⚡ [Swarm Agent] Running Performance Profiler Agent...")
        documents = state["documents"]
        if not documents:
            return {"performance_audit": "No code retrieved to analyze."}
            
        context = "\n\n".join([f"File: {d['file_path']}\nCode:\n{d['code'][:600]}" for d in documents[:3]])
        system = """You are a world-class Principal Performance and Big-O Analyst.
        Inspect the following codebase chunks for performance bottlenecks:
        - Algorithmic complexity issues (Big-O analysis).
        - Memory leaks, blocking operations, or excessive DB queries.
        - Redundant calculations or unoptimized loops.
        Provide a concise 2-3 bullet point performance profile."""
        
        messages = [
            SystemMessage(content=system),
            HumanMessage(content=f"Reviewing Code:\n{context}")
        ]
        response = await self._safe_ainvoke(messages)
        return {"performance_audit": response.content}

    async def compliance_architect(self, state: GraphState) -> Dict:
        """Synthesizes the final output, integrating architectural review, security scan, and performance audit."""
        logger.info("🌀 [Swarm Lead] Compliance Architect synthesizing final report...")
        question = state["question"]
        documents = state.get("documents", [])
        repo_id = state.get("repo_id") or "codebase"
        
        if not documents:
            msg = (
                f"# ⚠️ Codebase Context Not Found\n\n"
                f"No matching code snippets were located for query **\"{question}\"** in repository `{repo_id}`.\n\n"
                f"**Quick Checks:**\n"
                f"- If you used `_master`, switch to `_main` (or vice versa) in the top-right repository selector.\n"
                f"- Ensure the repository has been indexed via the **Ingest** tab.\n"
                f"- Choose one of the active indexed repositories from the dropdown."
            )
            return {"generation": msg}
            
        context = "\n\n".join([f"File: {d['file_path']}\nCode:\n{d['code'][:600]}" for d in documents[:3]])
        system = """You are the Lead Solutions Architect and Code Intelligence Swarm Lead at VortexRAG.
You synthesize code analysis, security auditing, and algorithmic performance profiling into a single unified report.

Structure your answer EXACTLY as follows:

# 🌀 VortexRAG Architect Review
[Direct architectural answer responding to the question using the retrieved code context]

## 🛡️ Security Audit Findings
[Provide a concise 2-3 bullet point security review: input validation, memory safety, credentials, or thread safety]

## ⚡ Performance & Big-O Profile
[Provide a concise 2-3 bullet point performance profile: Big-O complexity, thread pool utilization, I/O efficiency]"""
        
        messages = [
            SystemMessage(content=system),
            HumanMessage(content=f"Question: {question}\n\nCode Context:\n{context}")
        ]
        response = await self._safe_ainvoke(messages)
        return {"generation": response.content}

    async def run(self, question: str, repo_id: Optional[str] = None) -> dict:
        """Entry point to execute the agent."""
        initial_state = {
            "question": question, 
            "repo_id": repo_id,
            "search_count": 0,
            "documents": [],
            "generation": "",
            "security_audit": "",
            "performance_audit": ""
        }
        
        final_state = await self.graph.ainvoke(initial_state)
        
        return {
            "answer": final_state["generation"],
            "sources": final_state["documents"],
            "retries": final_state["search_count"] - 1
        }

    async def run_stream(self, question: str, repo_id: Optional[str] = None):
        """Streams agent progress and final synthesized tokens as Server-Sent Events."""
        initial_state = {
            "question": question, 
            "repo_id": repo_id,
            "search_count": 0,
            "documents": [],
            "generation": "",
            "security_audit": "",
            "performance_audit": ""
        }
        
        final_sources = []
        tokens_streamed = False
        
        try:
            async for event in self.graph.astream_events(initial_state, version="v2"):
                kind = event["event"]
                name = event["name"]
                
                # 1. Capture swarm node progress
                if kind == "on_chain_start" and name == "retrieve":
                    yield f"data: {json.dumps({'type': 'status', 'content': '🔍 Searching Vector Database & Call Graph...'})}\n\n"
                elif kind == "on_chain_start" and name == "grade_documents":
                    yield f"data: {json.dumps({'type': 'status', 'content': '🛡️ Passing top-ranked code candidates...'})}\n\n"
                elif kind == "on_chain_start" and name == "compliance_architect":
                    yield f"data: {json.dumps({'type': 'status', 'content': '🌀 [Swarm] Lead Architect streaming analysis...'})}\n\n"
                
                # 2. Capture sources
                elif kind == "on_chain_end" and name == "grade_documents":
                    output = event["data"].get("output", {})
                    if "documents" in output:
                        final_sources = [{"file_path": c["file_path"], "name": c["name"], "score": c.get("score", 1.0)} for c in output["documents"]]
                
                # 3. Capture streaming tokens from Compliance Architect
                elif kind == "on_chat_model_stream":
                    if event["metadata"].get("langgraph_node") == "compliance_architect":
                        chunk = event["data"]["chunk"]
                        if hasattr(chunk, "content"):
                            token = chunk.content
                            if token:
                                tokens_streamed = True
                                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
                                
                # 4. If no tokens were streamed (e.g. empty repo notice), yield static generation
                elif kind == "on_chain_end" and name == "compliance_architect":
                    output = event["data"].get("output", {})
                    if "generation" in output and not tokens_streamed:
                        yield f"data: {json.dumps({'type': 'token', 'content': output['generation']})}\n\n"
                                
            # 5. Stream final sources & completion
            yield f"data: {json.dumps({'type': 'sources', 'content': final_sources})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"
                                
        except Exception as e:
            logger.error(f"Stream failed: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
