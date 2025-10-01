# Test the complete proxy flow
# Replace {shop-domain} with your actual shop domain

# Test feedback submission via proxy
curl -X POST "https://{shop-domain}.myshopify.com/a/jarvis-proxy/feedback" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_proxy_123",
    "rating": 5,
    "feedback_text": "Testing proxy integration",
    "customer_name": "Proxy Test User",
    "customer_email": "proxy@test.com",
    "topic": "proxy_test"
  }'

# Test feedback session creation via proxy  
curl -X POST "https://{shop-domain}.myshopify.com/a/jarvis-proxy/feedback-session" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_proxy_session_123",
    "customer_name": "Proxy Session Test",
    "customer_email": "session@test.com",
    "conversation_topic": "Proxy Integration Testing"
  }'
