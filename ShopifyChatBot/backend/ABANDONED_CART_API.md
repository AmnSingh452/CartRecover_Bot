# 🛒 Abandoned Cart Discount API Documentation

## Overview
The `/api/abandoned-cart-discount` endpoint creates discount codes for abandoned cart recovery in Shopify stores.

## Endpoint Details
- **URL**: `POST /api/abandoned-cart-discount`
- **Content-Type**: `application/json`
- **CORS**: Enabled with wildcard origin (`*`)

## Request Format

### Required Fields
```json
{
  "session_id": "string",                              // Required: Session identifier
  "shop_domain": "aman-chatbot-test.myshopify.com",   // Required: Shopify store domain
  "discount_percentage": 10                            // Required: Discount percentage (1-100)
}
```

### Optional Fields
```json
{
  "customer_id": "string",        // Optional: Customer identifier
  "cart_data": {}                 // Optional: Cart data for tracking
}
```

### Complete Example Request
```json
{
  "session_id": "session_123",
  "shop_domain": "aman-chatbot-test.myshopify.com",
  "customer_id": "customer_456", 
  "cart_data": {
    "items": [
      {"product_id": "123", "quantity": 2},
      {"product_id": "456", "quantity": 1}
    ],
    "total": 99.99
  },
  "discount_percentage": 15
}
```

## Response Formats

### Success Response (200)
```json
{
  "discount_code": "SAVE15-ABC123",
  "message": "Discount created successfully"
}
```

### Error Responses

#### Missing Required Fields (400)
```json
{
  "error": "Missing shop_domain",
  "details": "shop_domain is required in request body"
}
```

#### Invalid Discount Percentage (400)
```json
{
  "error": "Invalid discount_percentage", 
  "details": "discount_percentage must be a number between 1 and 100"
}
```

#### Rate Limited (429)
```json
{
  "error": "Rate limit exceeded",
  "details": "You can only generate one discount code per hour. Please try again later.",
  "discount_codes": ["SAVE10-XYZ789"]
}
```

#### Server Error (500)
```json
{
  "error": "Failed to create discount code",
  "details": "Shopify API returned 403: Insufficient permissions"
}
```

## Discount Code Features

### Code Format
- Pattern: `SAVE{percentage}-{random_string}`
- Example: `SAVE20-ABC123` (20% discount)
- Random string: 6 characters (uppercase letters + digits)

### Discount Properties
- **Type**: Percentage discount
- **Value**: As specified in request (1-100%)
- **Usage Limit**: 1 per customer
- **Duration**: 24 hours from creation
- **Applies To**: Entire order
- **Customer Eligibility**: All customers

## CORS Support

### Preflight Request
```http
OPTIONS /api/abandoned-cart-discount
```

### CORS Headers
```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: POST, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
Access-Control-Max-Age: 3600
```

## Rate Limiting
- **Limit**: 1 discount code per session per hour
- **Scope**: Per session (not global)
- **Behavior**: Returns 429 status with existing codes

## Error Handling
All errors include:
- `error`: Brief error description
- `details`: Detailed error information for debugging
- CORS headers for cross-origin requests

## Authentication
- Uses shop domain to retrieve access token from database
- No additional authentication required for the endpoint
- Shopify store must be properly configured with valid access token

## Logging
All requests are logged with:
- 🛒 Request received with client IP
- 📝 Request payload details
- 🔗 Shopify API calls
- ✅/❌ Success/failure indicators
- 🎫 Generated discount codes

## Testing

### Using curl
```bash
curl -X POST http://localhost:8000/api/abandoned-cart-discount \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_123",
    "shop_domain": "aman-chatbot-test.myshopify.com",
    "discount_percentage": 20
  }'
```

### Using Python
```python
import requests

response = requests.post(
    "http://localhost:8000/api/abandoned-cart-discount",
    json={
        "session_id": "test_123",
        "shop_domain": "aman-chatbot-test.myshopify.com", 
        "discount_percentage": 20
    }
)

print(response.json())
```

## Integration Notes

### Shopify App Integration
1. Ensure your Shopify app has `write_discounts` permission
2. Store access tokens in database with shop domain as key
3. Handle webhook events for discount usage tracking

### Frontend Integration
```javascript
// Example JavaScript integration
const createDiscount = async (sessionId, percentage) => {
  try {
    const response = await fetch('/api/abandoned-cart-discount', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id: sessionId,
        shop_domain: 'your-store.myshopify.com',
        discount_percentage: percentage
      })
    });
    
    const result = await response.json();
    
    if (response.ok) {
      console.log('Discount created:', result.discount_code);
      return result.discount_code;
    } else {
      console.error('Error:', result.error);
      throw new Error(result.error);
    }
  } catch (error) {
    console.error('Network error:', error);
    throw error;
  }
};
```

## Troubleshooting

### Common Issues
1. **Shop not found**: Verify shop domain exists in database
2. **Permission denied**: Check Shopify app has `write_discounts` scope
3. **Rate limited**: Wait 1 hour or use different session
4. **Invalid percentage**: Use integer between 1-100

### Debug Steps
1. Check server logs for detailed error messages
2. Verify shop access token in database
3. Test with Shopify GraphQL explorer for API issues
4. Use the provided test script for endpoint validation
