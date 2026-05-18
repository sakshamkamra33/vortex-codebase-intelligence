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
        if not settings.GROQ_API_KEY:
            logger.warning("GROQ_API_KEY missing. Agent will fail.")
            
        from langchain_groq import ChatGroq
        self.llm = ChatGroq(
            model=settings.GROQ_MODEL,
            temperature=0,
            api_key=settings.GROQ_API_KEY
        )
        self.searcher = HybridSearcher()
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Constructs the LangGraph multi-agent swarm state machine."""
        workflow = StateGraph(GraphState)

        # Define nodes
        workflow.add_node("retrieve", self.retrieve)
        workflow.add_node("grade_documents", self.grade_documents)
        workflow.add_node("security_auditor", self.security_auditor)
        workflow.add_node("performance_profiler", self.performance_profiler)
        workflow.add_node("compliance_architect", self.compliance_architect)
        workflow.add_node("rewrite_query", self.rewrite_query)

        # Build graph structure
        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "grade_documents")
        
        # Parallel routing conditional edge
        workflow.add_conditional_edges(
            "grade_documents",
            self.decide_to_generate,
            {
                "audit": "security_auditor",
                "profile": "performance_profiler",
                "rewrite_query": "rewrite_query"
            }
        )
        
        # Join parallel nodes to Compliance Architect
        workflow.add_edge("security_auditor", "compliance_architect")
        workflow.add_edge("performance_profiler", "compliance_architect")
        
        workflow.add_edge("rewrite_query", "retrieve")
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
        """Determines whether the retrieved documents are relevant to the question."""
        question = state["question"]
        documents = state["documents"]
        
        logger.info("🤖 [Agent] Grading retrieved documents...")
        
        if not documents:
             return {"documents": [], "question": question}
             
        structured_llm_grader = self.llm.with_structured_output(GradeDocuments)
        
        system = """You are a grader assessing relevance of a retrieved code chunk to a user question. 
        If the document contains keyword(s) or semantic meaning related to the question, grade it as relevant. 
        Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question."""
        
        filtered_docs = []
        for doc in documents:
            messages = [
                SystemMessage(content=system),
                HumanMessage(content=f"Retrieved document: \n\n {doc['code']} \n\n User question: {question}")
            ]
            try:
                score = structured_llm_grader.invoke(messages)
                grade = score.binary_score
                if grade == "yes":
                    filtered_docs.append(doc)
            except Exception as e:
                logger.error(f"Grader failed: {e}")
                filtered_docs.append(doc)
                
        logger.info(f"🤖 [Agent] Kept {len(filtered_docs)} relevant documents out of {len(documents)}")
        return {"documents": filtered_docs, "question": question}

    async def security_auditor(self, state: GraphState) -> Dict:
        """Audits retrieved code context specifically for vulnerabilities in parallel."""
        logger.info("🛡️ [Swarm Agent] Running Security Auditor Agent...")
        documents = state["documents"]
        if not documents:
            return {"security_audit": "No code retrieved to audit."}
            
        context = "\n\n".join([f"File: {d['file_path']}\nCode:\n{d['code']}" for d in documents])
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
        response = await self.llm.ainvoke(messages)
        return {"security_audit": response.content}

    async def performance_profiler(self, state: GraphState) -> Dict:
        """Analyzes retrieved code for performance/algorithmic bottlenecks in parallel."""
        logger.info("⚡ [Swarm Agent] Running Performance Profiler Agent...")
        documents = state["documents"]
        if not documents:
            return {"performance_audit": "No code retrieved to analyze."}
            
        context = "\n\n".join([f"File: {d['file_path']}\nCode:\n{d['code']}" for d in documents])
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
        response = await self.llm.ainvoke(messages)
        return {"performance_audit": response.content}

    async def compliance_architect(self, state: GraphState) -> Dict:
        """Synthesizes the final output, integrating the security and performance audits."""
        logger.info("🌀 [Swarm Lead] Compliance Architect synthesizing final report...")
        question = state["question"]
        documents = state["documents"]
        security = state.get("security_audit") or "No security scan available."
        performance = state.get("performance_audit") or "No performance scan available."
        
        if not documents:
            return {"generation": "I couldn't find relevant code in the repository to answer your question."}
            
        context = "\n\n".join([f"File: {d['file_path']}\nCode:\n{d['code']}" for d in documents])
        system = """You are the Lead Solutions Architect. Synthesize findings from your specialized AI agent swarm.
        Write a premium, technical markdown report responding to the user's question, integrating the security and performance scans.
        
        Structure your answer EXACTLY as follows:
        
        # 🌀 VortexRAG Architect Review
        [Insert your direct architectural answer responding to the question using the retrieved code context]
        
        ## 🛡️ Security Audit Findings
        [Directly display or summarize the Security Auditor's profile findings]
        
        ## ⚡ Performance & Big-O Profile
        [Directly display or summarize the Performance Profiler's profile findings]"""
        
        messages = [
            SystemMessage(content=system),
            HumanMessage(content=f"Question: {question}\n\nCode Context:\n{context}\n\nSecurity Report:\n{security}\n\nPerformance Report:\n{performance}")
        ]
        response = await self.llm.ainvoke(messages)
        return {"generation": response.content}

    async def rewrite_query(self, state: GraphState) -> Dict:
        """Transforms the query to produce a better search if retrieval failed."""
        question = state["question"]
        logger.info("🤖 [Agent] Rewriting query to improve retrieval...")
        
        system = """You a question re-writer that converts an input question to a better version that is optimized 
        for vectorstore retrieval. Look at the input and try to reason about the underlying semantic intent / meaning."""
        
        messages = [
            SystemMessage(content=system),
            HumanMessage(content=f"Here is the initial question: {question} \n Formulate an improved question.")
        ]
        
        response = await self.llm.ainvoke(messages)
        return {"question": response.content}

    # ── Edge Logic ────────────────────────────────────────────────────────────
    def decide_to_generate(self, state: GraphState) -> List[str]:
        """Determines whether to trigger parallel Auditing agents or rewrite query."""
        filtered_docs = state["documents"]
        search_count = state.get("search_count", 0)
        
        if not filtered_docs:
            if search_count < 2:
                logger.info("🤖 [Agent] Decision: All docs irrelevant, REWRITE QUERY")
                return ["rewrite_query"]
            else:
                logger.info("🤖 [Agent] Decision: Max retries hit, GENERATE (with empty context)")
                return ["audit", "profile"]
                
        logger.info("🤖 [Agent] Decision: Found relevant docs, trigger Swarm Agents in parallel!")
        return ["audit", "profile"]

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
        
        try:
            async for event in self.graph.astream_events(initial_state, version="v2"):
                kind = event["event"]
                name = event["name"]
                
                # 1. Capture swarm node progress
                if kind == "on_chain_start" and name == "retrieve":
                    yield f"data: {json.dumps({'type': 'status', 'content': '🔍 Searching Vector Database...'})}\n\n"
                elif kind == "on_chain_start" and name == "grade_documents":
                    yield f"data: {json.dumps({'type': 'status', 'content': '🛡️ Grading retrieved code relevancy...'})}\n\n"
                elif kind == "on_chain_start" and name == "rewrite_query":
                    yield f"data: {json.dumps({'type': 'status', 'content': '🔄 Rewriting query to improve retrieval...'})}\n\n"
                elif kind == "on_chain_start" and name == "security_auditor":
                    yield f"data: {json.dumps({'type': 'status', 'content': '🛡️ [Swarm] Security Agent auditing vulnerabilities...'})}\n\n"
                elif kind == "on_chain_start" and name == "performance_profiler":
                    yield f"data: {json.dumps({'type': 'status', 'content': '⚡ [Swarm] Performance Agent profiling bottlenecks...'})}\n\n"
                elif kind == "on_chain_start" and name == "compliance_architect":
                    yield f"data: {json.dumps({'type': 'status', 'content': '🌀 [Swarm] Lead Architect synthesizing unified report...'})}\n\n"
                
                # 2. Capture sources
                elif kind == "on_chain_end" and name == "grade_documents":
                    output = event["data"]["output"]
                    if "documents" in output:
                        final_sources = [{"file_path": c["file_path"], "name": c["name"], "score": c.get("score", 1.0)} for c in output["documents"]]
                
                # 3. Capture streaming tokens from Compliance Architect
                elif kind == "on_chat_model_stream":
                    if event["metadata"].get("langgraph_node") == "compliance_architect":
                        chunk = event["data"]["chunk"]
                        if hasattr(chunk, "content"):
                            token = chunk.content
                            if token:
                                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
                                
            # 4. Stream final sources
            yield f"data: {json.dumps({'type': 'sources', 'content': final_sources})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"
                                
        except Exception as e:
            logger.error(f"Stream failed: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
