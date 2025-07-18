from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from routes.chatbot import router as chatbot_router
import logging
import time
from pydantic import BaseModel
from typing import Optional, Dict, Any
from routes import shopify
# Import shared instances from the new dependencies file
from dependencies import session_manager, agent_coordinator
import asyncpg

# Configure logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Shopify Chatbot API")
app.include_router(shopify.router)

# Configure CORS with more permissive settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
          "https://aman-chatbot-test.myshopify.com",
          
          # ...add more as needed
      ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Include routers
app.include_router(chatbot_router, prefix="/api")

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponseData(BaseModel):
    response: str
    session_id: str
    intent: Dict[str, Any]
    history: list
    customer_info: Optional[Dict[str, Any]] = None

class ApiResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None
    data: Optional[ChatResponseData] = None

class CustomerInfoUpdate(BaseModel):
    session_id: str
    name: Optional[str] = None
    email: Optional[str] = None

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"Request to {request.url.path} took {process_time:.2f} seconds")
    return response

@app.on_event("startup")
async def startup():
    app.state.db_pool = await asyncpg.create_pool(
        dsn="postgresql://chatbot_db_frvi_user:4pIoXTtZyZQ7Qnq4uaI8XLfaxFLMCDwy@dpg-d1sp3kre5dus73eg9cv0-a.oregon-postgres.render.com/chatbot_db_frvi"  # <-- fill in your DB info
    )

@app.get("/")
async def root():
    logger.info("Root endpoint called")
    return {"message": "Welcome to Shopify Chatbot API"}

@app.get("/ping")
async def ping():
    logger.info("Ping endpoint called")
    return {"message": "pong"}

# Dependency to get the DB pool
async def get_db_pool():
    # You should initialize this pool at app startup and reuse it
    # For demo, we'll assume it's globally available as app.state.db_pool
    return app.state.db_pool

async def get_shop_token(pool, shop_domain):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT access_token FROM shops WHERE shop_domain = $1",
            shop_domain
        )
        if not row:
            raise HTTPException(status_code=404, detail="Shop not found")
        return row["access_token"]

# Remove the /api/chat endpoint from this file. It is now handled in routes/chatbot.py

@app.get("/api/session/{session_id}")
async def get_session_history(session_id: str):
    logger.info(f"Getting history for session: {session_id}")
    history = session_manager.get_history(session_id)
    if history is None:
        logger.warning(f"Session not found: {session_id}")
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    return {"history": history}

@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    logger.info(f"Attempting to delete session: {session_id}")
    if session_manager.delete_session(session_id):
        return {"message": "Session deleted successfully"}
    logger.warning(f"Failed to delete session: {session_id}")
    raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

@app.get("/api/sessions")
async def list_sessions():
    """List all active sessions"""
    logger.info("Listing all active sessions")
    return {"sessions": list(session_manager.sessions.keys())}

@app.post("/api/customer/update")
async def update_customer_info(update: CustomerInfoUpdate):
    try:
        success = session_manager.update_customer_info(
            update.session_id,
            name=update.name,
            email=update.email
        )
        if success:
            return {"success": True, "message": "Customer information updated successfully"}
        else:
            raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        logger.error(f"Error updating customer info: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))