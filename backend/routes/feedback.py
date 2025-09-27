from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional
import logging
import asyncpg
from datetime import datetime
import uuid
from db import get_db_pool
from utils.response_format import success_response, error_response

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter()

class FeedbackRequest(BaseModel):
    session_id: str
    shop_domain: str
    rating: int  # 1-5 stars
    feedback_text: Optional[str] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    conversation_topic: Optional[str] = None

class FeedbackLinkRequest(BaseModel):
    session_id: str
    shop_domain: str
    customer_info: Optional[dict] = None

@router.post("/generate-feedback-link")
async def generate_feedback_link(request: FeedbackLinkRequest, pool=Depends(get_db_pool)):
    """
    Generate a unique feedback link for a customer after chat session ends
    Called via Shopify app proxy: /a/jarvis-proxy/feedback-session -> FastAPI /api/feedback/generate-feedback-link
    """
    try:
        logger.info(f"🔗 Generating feedback link for session: {request.session_id}")
        
        # Generate unique feedback token
        feedback_token = str(uuid.uuid4())
        
        # Store feedback session in database
        async with pool.acquire() as conn:
            # Convert customer_info dict to JSON string for database storage
            import json
            customer_info_json = json.dumps(request.customer_info) if request.customer_info else "{}"
            
            await conn.execute("""
                INSERT INTO feedback_sessions (
                    feedback_token, session_id, shop_domain, customer_info, 
                    created_at, expires_at, status
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, 
            feedback_token,
            request.session_id,
            request.shop_domain,
            customer_info_json,  # Now passing as JSON string
            datetime.utcnow(),
            datetime.utcnow().replace(hour=23, minute=59, second=59),  # Expires end of day
            'pending'
            )
        
        # Generate feedback URL (this will redirect to your Shopify app page)
        feedback_url = f"https://jarvis2-0-djg1.onrender.com/feedback/{feedback_token}"
        
        logger.info(f"✅ Generated feedback link: {feedback_url}")
        
        return success_response(
            data={
                "feedback_url": feedback_url,
                "feedback_token": feedback_token,
                "expires_at": datetime.utcnow().replace(hour=23, minute=59, second=59).isoformat()
            },
            message="Feedback link generated successfully"
        )
        
    except Exception as e:
        logger.error(f"❌ Error generating feedback link: {str(e)}")
        return error_response(
            message="Failed to generate feedback link",
            error=str(e)
        )

@router.post("/submit")
async def submit_feedback(request: FeedbackRequest, pool=Depends(get_db_pool)):
    """
    Submit customer feedback and save to database
    Called via Shopify app proxy: /a/jarvis-proxy/feedback -> FastAPI /api/feedback/submit
    """
    try:
        logger.info(f"📝 Receiving feedback for session: {request.session_id}")
        
        # Validate rating
        if not 1 <= request.rating <= 5:
            raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
        
        # Save feedback to database
        async with pool.acquire() as conn:
            feedback_id = await conn.fetchval("""
                INSERT INTO customer_feedback (
                    session_id, shop_domain, rating, feedback_text, 
                    customer_name, customer_email, conversation_topic, 
                    submitted_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
            """,
            request.session_id,
            request.shop_domain,
            request.rating,
            request.feedback_text,
            request.customer_name,
            request.customer_email,
            request.conversation_topic,
            datetime.utcnow()
            )
            
            # Update feedback session status
            await conn.execute("""
                UPDATE feedback_sessions 
                SET status = 'completed', completed_at = $1
                WHERE session_id = $2 AND shop_domain = $3
            """, datetime.utcnow(), request.session_id, request.shop_domain)
        
        # Send analytics event for satisfaction tracking
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                await client.post("https://jarvis2-0-djg1.onrender.com/api/analytics-event", json={
                    "eventType": "satisfaction",
                    "shopDomain": request.shop_domain,
                    "sessionId": request.session_id,
                    "data": {
                        "rating": request.rating,
                        "feedback_text": request.feedback_text,
                        "topic": request.conversation_topic
                    }
                })
        except Exception as analytics_error:
            logger.warning(f"⚠️ Failed to send analytics event: {analytics_error}")
        
        logger.info(f"✅ Feedback saved with ID: {feedback_id}")
        
        return success_response(
            data={
                "feedback_id": feedback_id,
                "rating": request.rating,
                "message": "Thank you for your feedback!"
            },
            message="Feedback submitted successfully"
        )
        
    except Exception as e:
        logger.error(f"❌ Error submitting feedback: {str(e)}")
        return error_response(
            message="Failed to submit feedback",
            error=str(e)
        )

@router.get("/analytics/{shop_domain}")
async def get_feedback_analytics(shop_domain: str, days: int = Query(30), pool=Depends(get_db_pool)):
    """
    Get feedback analytics for a shop
    """
    try:
        logger.info(f"📊 Getting feedback analytics for {shop_domain}")
        
        async with pool.acquire() as conn:
            # Get feedback summary
            feedback_stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_feedback,
                    AVG(rating)::NUMERIC(3,2) as avg_rating,
                    COUNT(CASE WHEN rating >= 4 THEN 1 END) as positive_feedback,
                    COUNT(CASE WHEN rating <= 2 THEN 1 END) as negative_feedback
                FROM customer_feedback 
                WHERE shop_domain = $1 
                AND submitted_at >= NOW() - INTERVAL '%s days'
            """ % days, shop_domain)
            
            # Get recent feedback
            recent_feedback = await conn.fetch("""
                SELECT 
                    id, session_id, rating, feedback_text, customer_name,
                    conversation_topic, submitted_at
                FROM customer_feedback 
                WHERE shop_domain = $1 
                AND submitted_at >= NOW() - INTERVAL '%s days'
                ORDER BY submitted_at DESC
                LIMIT 10
            """ % days, shop_domain)
            
            # Get daily feedback trends
            daily_trends = await conn.fetch("""
                SELECT 
                    DATE(submitted_at) as date,
                    COUNT(*) as feedback_count,
                    AVG(rating)::NUMERIC(3,2) as avg_rating
                FROM customer_feedback 
                WHERE shop_domain = $1 
                AND submitted_at >= NOW() - INTERVAL '%s days'
                GROUP BY DATE(submitted_at)
                ORDER BY date DESC
            """ % days, shop_domain)
            
            # Get feedback by topic
            topic_breakdown = await conn.fetch("""
                SELECT 
                    COALESCE(conversation_topic, 'General') as topic,
                    COUNT(*) as feedback_count,
                    AVG(rating)::NUMERIC(3,2) as avg_rating
                FROM customer_feedback 
                WHERE shop_domain = $1 
                AND submitted_at >= NOW() - INTERVAL '%s days'
                GROUP BY conversation_topic
                ORDER BY feedback_count DESC
            """ % days, shop_domain)
        
        return success_response(
            data={
                "summary": {
                    "total_feedback": feedback_stats['total_feedback'] or 0,
                    "average_rating": float(feedback_stats['avg_rating'] or 0),
                    "positive_feedback": feedback_stats['positive_feedback'] or 0,
                    "negative_feedback": feedback_stats['negative_feedback'] or 0,
                    "response_rate": "N/A"  # Can be calculated if you track total conversations
                },
                "recent_feedback": [
                    {
                        "id": row['id'],
                        "session_id": row['session_id'],
                        "rating": row['rating'],
                        "feedback_text": row['feedback_text'],
                        "customer_name": row['customer_name'] or "Anonymous",
                        "topic": row['conversation_topic'] or "General",
                        "submitted_at": row['submitted_at'].isoformat()
                    }
                    for row in recent_feedback
                ],
                "daily_trends": [
                    {
                        "date": row['date'].isoformat(),
                        "feedback_count": row['feedback_count'],
                        "avg_rating": float(row['avg_rating'] or 0)
                    }
                    for row in daily_trends
                ],
                "topic_breakdown": [
                    {
                        "topic": row['topic'],
                        "feedback_count": row['feedback_count'],
                        "avg_rating": float(row['avg_rating'] or 0)
                    }
                    for row in topic_breakdown
                ]
            },
            message="Feedback analytics retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"❌ Error getting feedback analytics: {str(e)}")
        return error_response(
            message="Failed to get feedback analytics",
            error=str(e)
        )

@router.get("/token/{feedback_token}")
async def get_feedback_session(feedback_token: str, pool=Depends(get_db_pool)):
    """
    Get feedback session details by token (for the feedback form)
    """
    try:
        async with pool.acquire() as conn:
            session_data = await conn.fetchrow("""
                SELECT 
                    session_id, shop_domain, customer_info, created_at, expires_at, status
                FROM feedback_sessions 
                WHERE feedback_token = $1 AND status = 'pending' AND expires_at > NOW()
            """, feedback_token)
            
            if not session_data:
                raise HTTPException(status_code=404, detail="Feedback session not found or expired")
            
            return success_response(
                data={
                    "session_id": session_data['session_id'],
                    "shop_domain": session_data['shop_domain'],
                    "customer_info": session_data['customer_info'],
                    "expires_at": session_data['expires_at'].isoformat()
                },
                message="Feedback session found"
            )
            
    except Exception as e:
        logger.error(f"❌ Error getting feedback session: {str(e)}")
        return error_response(
            message="Failed to get feedback session",
            error=str(e)
        )
