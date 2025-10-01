"""
Database migration script for customer feedback system
Run this script to create the necessary tables for customer feedback
"""

import asyncpg
import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def create_feedback_tables():
    """Create tables for customer feedback system"""
    
    # Connect to database
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
    
    try:
        print("🔄 Creating customer feedback tables...")
        
        # Create customer_feedback table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS customer_feedback (
                id SERIAL PRIMARY KEY,
                session_id VARCHAR(255) NOT NULL,
                shop_domain VARCHAR(255) NOT NULL,
                rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
                feedback_text TEXT,
                customer_name VARCHAR(255),
                customer_email VARCHAR(255),
                conversation_topic VARCHAR(100),
                submitted_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
            )
        """)
        print("✅ Created customer_feedback table")
        
        # Create feedback_sessions table (for managing feedback links)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS feedback_sessions (
                id SERIAL PRIMARY KEY,
                feedback_token VARCHAR(255) UNIQUE NOT NULL,
                session_id VARCHAR(255) NOT NULL,
                shop_domain VARCHAR(255) NOT NULL,
                customer_info JSONB,
                status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'expired')),
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
                expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
                completed_at TIMESTAMP WITHOUT TIME ZONE
            )
        """)
        print("✅ Created feedback_sessions table")
        
        # Create indexes for better performance
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_customer_feedback_shop_domain 
            ON customer_feedback(shop_domain)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_customer_feedback_session_id 
            ON customer_feedback(session_id)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_customer_feedback_submitted_at 
            ON customer_feedback(submitted_at)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_feedback_sessions_token 
            ON feedback_sessions(feedback_token)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_feedback_sessions_shop_domain 
            ON feedback_sessions(shop_domain)
        """)
        
        print("✅ Created database indexes")
        
        # Insert sample data for testing
        await conn.execute("""
            INSERT INTO customer_feedback (
                session_id, shop_domain, rating, feedback_text, 
                customer_name, conversation_topic, submitted_at
            ) VALUES 
            ('test-session-1', 'demo-store.myshopify.com', 5, 'Great chatbot! Very helpful with product information.', 'John Doe', 'Product Info', NOW() - INTERVAL '2 days'),
            ('test-session-2', 'demo-store.myshopify.com', 4, 'Good experience, found what I was looking for.', 'Jane Smith', 'General', NOW() - INTERVAL '1 day'),
            ('test-session-3', 'demo-store.myshopify.com', 3, 'Okay service, could be more responsive.', 'Bob Johnson', 'Shipping', NOW() - INTERVAL '3 hours'),
            ('test-session-4', 'demo-store.myshopify.com', 5, 'Excellent! The bot understood my complex query perfectly.', 'Alice Brown', 'Order Status', NOW() - INTERVAL '1 hour'),
            ('test-session-5', 'demo-store.myshopify.com', 2, 'Had trouble getting the right product recommendations.', 'Mike Wilson', 'Product Info', NOW() - INTERVAL '30 minutes')
            ON CONFLICT DO NOTHING
        """)
        print("✅ Inserted sample feedback data")
        
        print("\n🎉 Database migration completed successfully!")
        print("\n📊 Tables created:")
        print("   • customer_feedback - Stores customer ratings and feedback")
        print("   • feedback_sessions - Manages feedback links and tokens")
        print("\n🔍 Sample API endpoints available:")
        print("   • POST /api/feedback/generate-feedback-link")
        print("   • POST /api/feedback/submit")
        print("   • GET /api/feedback/analytics/{shop_domain}")
        print("   • GET /api/feedback/token/{feedback_token}")
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(create_feedback_tables())
