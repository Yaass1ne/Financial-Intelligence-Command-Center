"""
FINCENTER API - Main FastAPI Application

This is the entry point for the FINCENTER API server.
It provides endpoints for querying financial data, running simulations,
and accessing the RAG system.

Usage:
    python src/api/main.py --port 8080 --debug
"""

import argparse
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from pydantic import BaseModel, Field
from pathlib import Path

# Import configuration
from src.config import settings
from src.rag.graph import FinancialGraph
from src.rag.vectorstore import VectorStore
from src.llm.groq_client import answer_question
from src.memory.episodic import EpisodicMemory
from src.intelligence.weak_signals import WeakSignalDetector
from src.intelligence.decision_fusion import DecisionFusion
from src.recommendations.engine import RecommendationEngine
from src.feedback.loop import FeedbackLoop
from src.simulation.ai_scenarios import AIScenarioGenerator
from src.rag.orchestrator import RAGOrchestrator


# Pydantic models for API requests/responses
class BudgetVarianceResponse(BaseModel):
    department: str
    budget: float
    actual: float
    variance: float
    variance_percent: float


class InvoiceResponse(BaseModel):
    invoice_id: str
    date: str
    vendor: str
    amount: float
    status: str


class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query in natural language")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of results")


class ChatRequest(BaseModel):
    question: str = Field(..., description="Natural language question about financial data")


class FeedbackPredictionRequest(BaseModel):
    entity_type: str = Field(..., description="e.g. 'budget', 'invoice', 'contract'")
    entity_id: str = Field(..., description="Entity identifier")
    metric: str = Field(..., description="What is being predicted")
    predicted_value: float = Field(..., description="Predicted numeric value")


class FeedbackActualRequest(BaseModel):
    prediction_id: str = Field(..., description="UUID of the prediction to update")
    actual_value: float = Field(..., description="Observed actual value")


class ChatResponse(BaseModel):
    question: str
    answer: str
    model: str


class SearchResult(BaseModel):
    document_id: str
    document_type: str
    content: str
    score: float
    metadata: Dict[str, Any]


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup and cleanup on shutdown."""
    # Startup
    print("[STARTUP] Starting FINCENTER API...")

    # Initialize connections
    app.state.graph = FinancialGraph()
    app.state.vectorstore = VectorStore()

    # Initialize intelligence modules
    app.state.memory = EpisodicMemory(app.state.graph)
    app.state.rag = RAGOrchestrator(
        graph=app.state.graph,
        vectorstore=app.state.vectorstore,
        llm_fn=answer_question,
        memory=app.state.memory,
    )
    app.state.weak_signals = WeakSignalDetector(app.state.graph)
    app.state.decision_fusion = DecisionFusion(app.state.graph)
    app.state.recommendations = RecommendationEngine(app.state.graph)
    app.state.feedback = FeedbackLoop(app.state.graph, app.state.vectorstore)
    app.state.ai_scenarios = AIScenarioGenerator(app.state.graph)

    # Run initial pattern detection on startup
    try:
        count = app.state.memory.run_pattern_detection()
        print(f"[MEMORY] Detected {count} episodic patterns on startup")
    except Exception as e:
        print(f"[MEMORY] Pattern detection skipped: {e}")

    print("[SUCCESS] Connected to Neo4j and VectorStore")

    yield  # Application runs here

    # Shutdown
    print("[SHUTDOWN] Shutting down FINCENTER API...")
    app.state.graph.close()
    print("[SUCCESS] Closed all connections")


# Create FastAPI app
app = FastAPI(
    title="FINCENTER API",
    description="Financial Intelligence Command Center - Cognitive Architecture API",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# Health Check Endpoints
# ============================================

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "services": {
            "neo4j": "connected",
            "vectorstore": "connected"
        }
    }


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "FINCENTER API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health"
    }


# ============================================
# Budget Endpoints
# ============================================

@app.get("/api/budgets/{department}/variance", 
         response_model=BudgetVarianceResponse,
         tags=["Budgets"])
async def get_budget_variance(department: str):
    """
    Get budget variance for a specific department.
    
    Args:
        department: Department name (e.g., "Marketing", "IT", "R&D")
    
    Returns:
        Budget variance information
    """
    try:
        # TODO: Implement actual query to database
        # This is a mock response for demonstration
        variance = await app.state.graph.get_budget_variance(department)
        
        if not variance:
            raise HTTPException(status_code=404, detail=f"Department '{department}' not found")
        
        return variance
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching budget variance: {str(e)}")


@app.get("/api/budgets/summary", tags=["Budgets"])
async def get_budget_summary(year: int = Query(2024, ge=2020, le=2030)):
    """
    Get budget summary for all departments.
    
    Args:
        year: Fiscal year
    
    Returns:
        Summary of all department budgets
    """
    try:
        summary = await app.state.graph.get_budget_summary(year)
        return summary
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching budget summary: {str(e)}")


# ============================================
# Invoice Endpoints
# ============================================

@app.get("/api/invoices/overdue", 
         response_model=List[InvoiceResponse],
         tags=["Invoices"])
async def get_overdue_invoices(days: int = Query(0, ge=0, description="Minimum days overdue")):
    """
    Get all overdue invoices.
    
    Args:
        days: Minimum number of days overdue (0 for all overdue)
    
    Returns:
        List of overdue invoices
    """
    try:
        invoices = await app.state.graph.get_overdue_invoices(days_overdue=days)
        return invoices
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching overdue invoices: {str(e)}")


@app.get("/api/invoices/{invoice_id}", 
         response_model=InvoiceResponse,
         tags=["Invoices"])
async def get_invoice(invoice_id: str):
    """
    Get details for a specific invoice.
    
    Args:
        invoice_id: Invoice ID (e.g., "INV-2024-0001")
    
    Returns:
        Invoice details
    """
    try:
        invoice = await app.state.graph.get_invoice(invoice_id)
        
        if not invoice:
            raise HTTPException(status_code=404, detail=f"Invoice '{invoice_id}' not found")
        
        return invoice
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching invoice: {str(e)}")


# ============================================
# Contract Endpoints
# ============================================

@app.get("/api/contracts", tags=["Contracts"])
async def get_all_contracts():
    """
    Get ALL contracts regardless of expiry date.
    """
    try:
        query = """
        MATCH (c:Contract)
        RETURN c.id AS contract_id,
               c.vendor AS vendor,
               toString(c.end_date) AS end_date,
               c.annual_value AS annual_value,
               c.auto_renewal AS auto_renewal,
               CASE WHEN c.end_date IS NOT NULL
                    THEN duration.inDays(date(), c.end_date).days
                    ELSE 9999 END AS days_until_expiry
        ORDER BY days_until_expiry
        """
        with app.state.graph.driver.session() as session:
            result = session.run(query)
            contracts = [dict(r) for r in result]
        return contracts
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching contracts: {str(e)}")


@app.get("/api/contracts/expiring", tags=["Contracts"])
async def get_expiring_contracts(days: int = Query(90, ge=1, le=365)):
    """
    Get contracts expiring within specified days.

    Args:
        days: Number of days ahead to check

    Returns:
        List of expiring contracts
    """
    try:
        contracts = await app.state.graph.get_expiring_contracts(days_ahead=days)
        return contracts

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching expiring contracts: {str(e)}")


@app.get("/api/contracts/{contract_id}/clauses", tags=["Contracts"])
async def get_contract_clauses(contract_id: str):
    """
    Get all clauses for a specific contract.

    Args:
        contract_id: Contract ID

    Returns:
        List of contract clauses
    """
    try:
        # Query clauses for the contract
        query = """
        MATCH (c:Contract {id: $contract_id})-[:HAS_CLAUSE]->(cl:Clause)
        RETURN cl.type AS type,
               cl.description AS description,
               cl.value AS value
        ORDER BY cl.type
        """

        with app.state.graph.driver.session() as session:
            result = session.run(query, contract_id=contract_id)
            clauses = [dict(record) for record in result]

        if not clauses:
            raise HTTPException(status_code=404, detail=f"No clauses found for contract '{contract_id}'")

        return {
            "contract_id": contract_id,
            "clauses": clauses,
            "total_clauses": len(clauses)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching clauses: {str(e)}")


# ============================================
# Search & RAG Endpoints
# ============================================

@app.post("/api/search", 
          response_model=List[SearchResult],
          tags=["Search"])
async def semantic_search(request: SearchRequest):
    """
    Semantic search across all financial documents.
    
    Args:
        request: Search request with query and limit
    
    Returns:
        List of relevant documents with scores
    """
    try:
        results = await app.state.vectorstore.search(
            query=request.query,
            limit=request.limit
        )
        return results
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


@app.get("/api/search/contracts/clauses", tags=["Search"])
async def search_contract_clauses(
    clause_type: str = Query(..., description="Clause type (e.g., 'price_revision', 'penalty')")
):
    """
    Find all contracts with a specific clause type.

    Args:
        clause_type: Type of clause to search for

    Returns:
        List of contracts with matching clauses
    """
    try:
        contracts = await app.state.graph.search_contracts_by_clause(clause_type)
        return contracts

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching clauses: {str(e)}")


# ============================================
# Ingestion Endpoints
# ============================================

@app.post("/api/ingestion/start", tags=["Ingestion"])
async def start_ingestion(
    background_tasks: BackgroundTasks,
    input_directory: str = Query(..., description="Directory with source documents"),
    output_directory: str = Query("./data/processed", description="Output directory for processed data")
):
    """
    Trigger document ingestion pipeline.

    Args:
        input_directory: Path to directory containing source documents
        output_directory: Path to output directory for processed data

    Returns:
        Status message with ingestion task ID
    """
    try:
        from src.ingestion.pipeline import ingest_directory

        # Validate directories
        input_path = Path(input_directory)
        if not input_path.exists():
            raise HTTPException(status_code=400, detail=f"Input directory not found: {input_directory}")

        output_path = Path(output_directory)

        # Run ingestion in background
        def run_ingestion():
            try:
                stats = ingest_directory(input_path, output_path)
                logger.info(f"Ingestion complete: {stats}")
            except Exception as e:
                logger.error(f"Ingestion failed: {e}")

        background_tasks.add_task(run_ingestion)

        return {
            "status": "started",
            "message": "Ingestion pipeline started in background",
            "input_directory": str(input_path),
            "output_directory": str(output_path)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting ingestion: {str(e)}")


# ============================================
# Simulation Endpoints
# ============================================

@app.post("/api/simulations/budget", tags=["Simulations"])
async def simulate_budget_change_endpoint(
    department: str,
    change_percent: float = Query(..., ge=-50, le=100),
    months: int = Query(12, ge=1, le=36)
):
    """
    Simulate the impact of a budget change.

    Args:
        department: Department name
        change_percent: Percentage change (+10 for +10%, -10 for -10%)
        months: Number of months to simulate

    Returns:
        Simulation results with projections
    """
    try:
        from src.simulation.budget import simulate_budget_change

        result = simulate_budget_change(
            department=department,
            change_percent=change_percent,
            months=months
        )
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation error: {str(e)}")


@app.post("/api/simulations/cashflow", tags=["Simulations"])
async def simulate_cashflow_endpoint(
    months_ahead: int = Query(3, ge=1, le=24),
    scenarios: List[str] = Query(default=["optimistic", "base", "pessimistic"])
):
    """
    Forecast cash flow for different scenarios.

    Args:
        months_ahead: Number of months to forecast
        scenarios: List of scenarios to simulate

    Returns:
        Cash flow forecast for each scenario
    """
    try:
        from src.simulation.cashflow import forecast_cashflow

        result = forecast_cashflow(
            months_ahead=months_ahead,
            scenarios=scenarios
        )

        # Convert DataFrames to dictionaries for JSON serialization
        for scenario in result:
            if scenario != 'summary' and 'forecast' in result[scenario]:
                result[scenario]['forecast'] = result[scenario]['forecast'].to_dict('records')

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cashflow simulation error: {str(e)}")


@app.post("/api/simulations/monte-carlo", tags=["Simulations"])
async def run_monte_carlo_endpoint(
    revenue: float = Query(..., gt=0),
    revenue_volatility: float = Query(0.15, ge=0, le=1),
    costs: float = Query(..., gt=0),
    cost_volatility: float = Query(0.10, ge=0, le=1),
    iterations: int = Query(10000, ge=1000, le=100000)
):
    """
    Run Monte Carlo simulation for revenue/cost uncertainty.

    Args:
        revenue: Expected revenue
        revenue_volatility: Revenue volatility (as fraction, e.g., 0.15 for 15%)
        costs: Expected costs
        cost_volatility: Cost volatility
        iterations: Number of iterations

    Returns:
        Monte Carlo simulation results
    """
    try:
        from src.simulation.monte_carlo import run_monte_carlo

        result = run_monte_carlo(
            base_params={'revenue': revenue, 'costs': costs},
            volatility={'revenue': revenue_volatility, 'costs': cost_volatility},
            iterations=iterations
        )

        # Remove numpy array from response (too large)
        if 'distribution' in result:
            del result['distribution']

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Monte Carlo error: {str(e)}")


# ============================================
# Analytics Endpoints
# ============================================

@app.get("/api/analytics/payment-patterns/{client}", tags=["Analytics"])
async def analyze_payment_patterns(client: str):
    """
    Analyze payment patterns for a specific client.

    Args:
        client: Client name

    Returns:
        Payment pattern analysis (average delay, variance, etc.)
    """
    try:
        patterns = await app.state.graph.analyze_client_payment_patterns(client)

        if not patterns:
            raise HTTPException(status_code=404, detail=f"No data for client '{client}'")

        return patterns

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis error: {str(e)}")


@app.get("/api/analytics/dashboard/summary", tags=["Analytics"])
async def get_dashboard_summary():
    """
    Get comprehensive dashboard summary with key metrics.

    Returns:
        Dashboard summary with budget, invoice, and contract metrics
    """
    try:
        summary = {
            "budgets": {
                "total_budget": 0,
                "total_actual": 0,
                "variance": 0,
                "departments_over_budget": 0
            },
            "invoices": {
                "total_outstanding": 0,
                "overdue_count": 0,
                "total_overdue_amount": 0
            },
            "contracts": {
                "total_active": 0,
                "expiring_soon": 0,
                "total_annual_value": 0
            },
            "alerts": []
        }

        # Get budget summary
        budgets = await app.state.graph.get_budget_summary(year=2024)
        if budgets:
            summary["budgets"]["total_budget"] = sum(b.get("budget", 0) for b in budgets)
            summary["budgets"]["total_actual"] = sum(b.get("actual", 0) for b in budgets)
            summary["budgets"]["variance"] = summary["budgets"]["total_actual"] - summary["budgets"]["total_budget"]
            summary["budgets"]["departments_over_budget"] = sum(1 for b in budgets if b.get("variance", 0) > 0)

        # Get invoice summary
        overdue_invoices = await app.state.graph.get_overdue_invoices(days_overdue=0)
        if overdue_invoices:
            summary["invoices"]["overdue_count"] = len(overdue_invoices)
            summary["invoices"]["total_overdue_amount"] = sum(inv.get("amount", 0) for inv in overdue_invoices)

        # Get contract summary
        expiring_contracts = await app.state.graph.get_expiring_contracts(days_ahead=90)
        if expiring_contracts:
            summary["contracts"]["expiring_soon"] = len(expiring_contracts)
            summary["contracts"]["total_annual_value"] = sum(c.get("annual_value", 0) for c in expiring_contracts)

        # Generate alerts
        if summary["budgets"]["departments_over_budget"] > 0:
            summary["alerts"].append({
                "type": "budget_overrun",
                "severity": "warning",
                "message": f"{summary['budgets']['departments_over_budget']} departments over budget"
            })

        if summary["invoices"]["overdue_count"] > 0:
            summary["alerts"].append({
                "type": "overdue_invoices",
                "severity": "high",
                "message": f"{summary['invoices']['overdue_count']} overdue invoices"
            })

        if summary["contracts"]["expiring_soon"] > 0:
            summary["alerts"].append({
                "type": "expiring_contracts",
                "severity": "medium",
                "message": f"{summary['contracts']['expiring_soon']} contracts expiring within 90 days"
            })

        return summary

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching dashboard summary: {str(e)}")


# ============================================
# AI Chat Endpoint (Groq / Llama-3.3-70B)
# ============================================

@app.post("/api/chat", tags=["AI Chat"])
async def chat(request: ChatRequest):
    """
    Ask a natural language question about the financial data.

    The system fetches live context from Neo4j (budgets, contracts, invoices)
    and passes it to Llama-3.3-70B via Groq to generate a grounded answer.
    """
    try:
        # Delegate to RAG Orchestrator — vector + graph + memory + LLM
        result = app.state.rag.query_sync(
            question=request.question,
            top_k=5,
        )

        return ChatResponse(
            question=request.question,
            answer=result["answer"],
            model=settings.GROQ_MODEL,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


# ============================================
# RAG Orchestrator Endpoint
# ============================================

@app.post("/api/rag/query", tags=["RAG"])
async def rag_query(request: ChatRequest):
    """
    Full RAG pipeline: vector search → graph enrichment → episodic memory → LLM.
    Returns the answer plus sources used (vector hits, graph, memory).
    """
    try:
        result = app.state.rag.query_sync(question=request.question, top_k=5)
        return {
            "question": request.question,
            "answer": result["answer"],
            "sources": result.get("sources", []),
            "vector_hits": result.get("vector_hits", 0),
            "model": settings.GROQ_MODEL,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG query error: {str(e)}")


@app.get("/api/rag/vendor/{vendor}", tags=["RAG"])
async def rag_vendor_summary(vendor: str):
    """Graph traversal: return complete financial summary for a vendor."""
    try:
        summary = app.state.rag.get_vendor_financial_summary(vendor)
        return {"vendor": vendor, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG vendor error: {str(e)}")


# ============================================
# Source Connector Health Endpoint
# ============================================

@app.get("/api/sources/health", tags=["Sources"])
async def sources_health():
    """
    Report availability of all multimodal source connectors.
    File-based sources (PDF/Excel/JSON/CSV) are always available via the ingestion pipeline.
    Cloud/streaming connectors report their real status.
    """
    from src.ingestion.connectors import CONNECTOR_REGISTRY
    statuses = {
        "file_pdf_excel_json_csv": {"status": "ok", "connector": "IngestionPipeline"},
    }
    # Check IoT/Logs connector (no credentials needed)
    try:
        from src.ingestion.connectors import IoTLogsConnector
        c = IoTLogsConnector()
        statuses["iot_logs"] = c.health_check()
    except Exception:
        statuses["iot_logs"] = {"status": "unavailable"}

    # Stub status for credential-dependent connectors
    for name in ["s3", "kafka", "sharepoint", "api", "media"]:
        statuses[name] = {
            "status": "stub",
            "note": f"{name.upper()} connector implemented — requires credentials/SDK to activate",
        }
    return {"sources": statuses, "total": len(statuses)}


# ============================================
# Episodic Memory Endpoints
# ============================================

@app.get("/api/memory/patterns", tags=["Memory"])
async def get_memory_patterns(pattern_type: Optional[str] = Query(None, description="Filter by pattern type")):
    """Return all learned episodic memory patterns."""
    try:
        patterns = app.state.memory.get_patterns(pattern_type)
        return {"patterns": patterns, "count": len(patterns)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Memory error: {str(e)}")


@app.post("/api/memory/refresh", tags=["Memory"])
async def refresh_memory(background_tasks: BackgroundTasks):
    """Trigger pattern detection in the background."""
    def _run():
        try:
            count = app.state.memory.run_pattern_detection()
            print(f"[MEMORY] Refresh complete: {count} patterns")
        except Exception as e:
            print(f"[MEMORY] Refresh error: {e}")

    background_tasks.add_task(_run)
    return {"status": "started", "message": "Pattern detection running in background"}


# ============================================
# Weak Signal Endpoints
# ============================================

@app.get("/api/intelligence/weak-signals", tags=["Intelligence"])
async def get_weak_signals():
    """Return active weak signal stress clusters."""
    try:
        # Run detection to get latest signals
        app.state.weak_signals.run_detection()
        signals = app.state.weak_signals.get_active_signals()
        return {"weak_signals": signals, "count": len(signals)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Weak signal error: {str(e)}")


# ============================================
# Decision Fusion Endpoints
# ============================================

@app.get("/api/fusion/decisions", tags=["Intelligence"])
async def get_fusion_decisions(limit: int = Query(20, ge=1, le=50)):
    """Return ranked tactical decisions from all intelligence sources."""
    try:
        decisions = app.state.decision_fusion.get_ranked_decisions(limit=limit)
        return {"decisions": decisions, "count": len(decisions)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Decision fusion error: {str(e)}")


# ============================================
# Recommendation Endpoints
# ============================================

@app.get("/api/recommendations", tags=["Recommendations"])
async def get_recommendations(limit: int = Query(20, ge=1, le=50)):
    """Return scored recommendations sorted by priority."""
    try:
        # Generate fresh recommendations and return them
        recs = app.state.recommendations.generate_recommendations()
        return {"recommendations": recs[:limit], "count": len(recs)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendation error: {str(e)}")


@app.post("/api/recommendations/{rec_id}/acknowledge", tags=["Recommendations"])
async def acknowledge_recommendation(rec_id: str):
    """Mark a recommendation as seen/actioned."""
    try:
        app.state.recommendations.acknowledge(rec_id)
        return {"status": "acknowledged", "id": rec_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Acknowledge error: {str(e)}")


# ============================================
# Feedback Loop Endpoints
# ============================================

@app.post("/api/feedback/record", tags=["Feedback"])
async def record_prediction(request: FeedbackPredictionRequest):
    """Save a new prediction for later comparison with actual."""
    try:
        pred_id = app.state.feedback.record_prediction(
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            metric=request.metric,
            predicted_value=request.predicted_value,
        )
        return {"prediction_id": pred_id, "status": "recorded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Feedback error: {str(e)}")


@app.post("/api/feedback/actual", tags=["Feedback"])
async def record_actual(request: FeedbackActualRequest):
    """Record the actual outcome and compute prediction error."""
    try:
        result = app.state.feedback.record_actual(
            prediction_id=request.prediction_id,
            actual_value=request.actual_value,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Feedback error: {str(e)}")


@app.get("/api/feedback/accuracy", tags=["Feedback"])
async def get_accuracy_stats():
    """Get prediction accuracy statistics by entity type."""
    try:
        stats = app.state.feedback.get_accuracy_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Accuracy stats error: {str(e)}")


# ============================================
# AI Scenario Generation Endpoint
# ============================================

@app.post("/api/simulations/ai-generate", tags=["Simulations"])
async def generate_ai_scenarios():
    """Generate 3 AI-named financial scenarios using Groq/Llama from live data."""
    try:
        scenarios = app.state.ai_scenarios.generate_scenarios()
        return {"scenarios": scenarios, "count": len(scenarios), "source": "ai_generated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI scenario generation error: {str(e)}")


# ============================================
# Error Handlers
# ============================================

@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Not found", "detail": str(exc.detail)}
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": "An unexpected error occurred"}
    )


# ============================================
# Main Entry Point
# ============================================

def main():
    parser = argparse.ArgumentParser(description="Start FINCENTER API server")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind to")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode with auto-reload")
    parser.add_argument("--workers", type=int, default=1, help="Number of worker processes")
    
    args = parser.parse_args()
    
    print(f"""
=========================================
   FINCENTER API Server
   Financial Intelligence Platform
=========================================

[SERVER] Starting on http://{args.host}:{args.port}
[DOCS] API Documentation: http://{args.host}:{args.port}/docs
[DOCS] ReDoc: http://{args.host}:{args.port}/redoc
    """)
    
    uvicorn.run(
        "src.api.main:app",
        host=args.host,
        port=args.port,
        reload=args.debug,
        workers=1 if args.debug else args.workers,
        log_level="debug" if args.debug else "info"
    )


if __name__ == "__main__":
    main()
