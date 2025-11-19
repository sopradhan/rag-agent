"""
FastAPI Backend for RAG Agent System
Serves React frontend and provides REST API endpoints
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import sys
import logging
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.orchestrator import MasterOrchestrator
from src.agents.parent_agents import IngestionAgent, RetrievalAgent, HealingAgent
from src.abstraction import Document
from src.storage import RAGDatabase

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="RAG Agent System API",
    description="Interactive REST API for RAG document processing",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agents globally
orchestrator = MasterOrchestrator(name="api_orchestrator")
ingestion_agent = IngestionAgent(use_intelligent_rbac=True)
retrieval_agent = RetrievalAgent(use_intelligent_rbac=True)
healing_agent = HealingAgent(use_intelligent_rbac=True)
db = orchestrator.db

# Pydantic models
class ChatMessage(BaseModel):
    message: str
    user_role: str = "engineer"
    session: str = "default"

class ChatResponse(BaseModel):
    content: str
    actions: List[str] = []
    timestamp: str

class StatsResponse(BaseModel):
    total_documents: int
    queries_24h: int
    avg_response_time: float
    success_rate: float
    agent_spawns_24h: int
    healing_ops_24h: int

# Routes

@app.get("/", tags=["Frontend"])
async def root():
    """Serve the React frontend"""
    return FileResponse("frontend/build/index.html")

@app.get("/api/health", tags=["System"])
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

@app.get("/api/stats", response_model=StatsResponse, tags=["Analytics"])
async def get_stats():
    """Get system statistics"""
    try:
        stats = orchestrator.dashboard_statistics()
        return StatsResponse(
            total_documents=stats.get('total_documents', 0),
            queries_24h=stats.get('queries_24h', 0),
            avg_response_time=stats.get('avg_response_time', 0),
            success_rate=stats.get('success_rate', 0),
            agent_spawns_24h=stats.get('agent_spawns_24h', 0),
            healing_ops_24h=stats.get('healing_ops_24h', 0)
        )
    except Exception as e:
        logger.error(f"Error fetching stats: {str(e)}")
        return StatsResponse(
            total_documents=0,
            queries_24h=0,
            avg_response_time=0,
            success_rate=0,
            agent_spawns_24h=0,
            healing_ops_24h=0
        )

@app.post("/api/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(message: ChatMessage):
    """Process chat message and route to appropriate agent"""
    try:
        # Route command through orchestrator
        routing = orchestrator.route_command(message.message)
        intent = routing.get("intent")
        
        # Map user role to access level
        role_to_level = {
            "intern": 1,
            "junior": 2,
            "engineer": 3,
            "lead": 4,
            "admin": 5
        }
        access_level = role_to_level.get(message.user_role, 3)
        
        response_content = ""
        actions = []
        
        if intent == "retrieve":
            # Call retrieval agent
            user_data = {
                "id": 1,
                "role": message.user_role,
                "access_level": access_level
            }
            result = retrieval_agent.execute(message.message, user_data)
            response_content = f"🔍 **Search Results**\n\nFound {result.get('count', 0)} documents matching your query."
            actions = ["View Details", "Export Results", "Ask Follow-up"]
            
        elif intent == "ingest":
            response_content = "📤 **Ready to Ingest Documents**\n\nPlease upload a file using the upload button."
            actions = ["Upload File", "Batch Upload", "Cancel"]
            
        elif intent == "heal":
            # Call healing agent
            result = healing_agent.execute(healing_mode="full")
            response_content = "⚕️ **System Healing Complete**\n\nVector store optimized and indexes rebuilt."
            actions = ["View Report", "Run Quick Check"]
        
        else:
            response_content = "I can help you with:\n• Searching documents\n• Ingesting new documents\n• Optimizing the system\n\nWhat would you like to do?"
            actions = ["Search", "Ingest", "Optimize"]
        
        return ChatResponse(
            content=response_content,
            actions=actions,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error in chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload", tags=["Ingestion"])
async def upload_file(file: UploadFile = File(...)):
    """Upload and ingest a document"""
    try:
        content = await file.read()
        content_text = content.decode('utf-8')
        
        # Create document
        doc = Document(
            id=f"doc_{file.filename.replace('.', '_')}",
            content=content_text,
            title=file.filename,
            source="web_upload",
            metadata={
                "filename": file.filename,
                "size": len(content),
                "uploaded_at": datetime.now().isoformat()
            }
        )
        
        # Ingest document
        result = ingestion_agent.execute([doc])
        
        return {
            "status": "success",
            "filename": file.filename,
            "documents_ingested": len(result),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/search", tags=["Retrieval"])
async def search(query: str, user_role: str = "engineer"):
    """Search documents"""
    try:
        role_to_level = {
            "intern": 1,
            "junior": 2,
            "engineer": 3,
            "lead": 4,
            "admin": 5
        }
        access_level = role_to_level.get(user_role, 3)
        
        user_data = {
            "id": 1,
            "role": user_role,
            "access_level": access_level
        }
        
        result = retrieval_agent.execute(query, user_data)
        
        return {
            "query": query,
            "count": result.get('count', 0),
            "documents": result.get('documents', []),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/heal", tags=["System"])
async def heal_system(mode: str = "full"):
    """Heal and optimize the system"""
    try:
        result = healing_agent.execute(healing_mode=mode)
        
        return {
            "status": "success",
            "mode": mode,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in healing: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions", tags=["Session"])
async def get_sessions():
    """Get user sessions"""
    return {
        "sessions": ["Session 1", "Session 2", "Session 3"],
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
