// These routes should be added to your Shopify Remix app (jarvis2-0-djg1.onrender.com)
// File: app/routes/app.jarvis-proxy.feedback-session.jsx

import { json } from "@remix-run/node";

// CORS headers for all responses
const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
  "Access-Control-Max-Age": "86400"
};

// Handle OPTIONS preflight requests
export async function options() {
  return new Response(null, {
    status: 200,
    headers: corsHeaders
  });
}

// Handle POST requests for feedback session creation
export async function action({ request }) {
  try {
    const body = await request.json();
    const { shop } = new URL(request.url).searchParams;
    
    // Forward the request to your FastAPI backend
    const backendUrl = "YOUR_FASTAPI_BACKEND_URL"; // Replace with your actual backend URL
    
    const response = await fetch(`${backendUrl}/api/feedback/generate-feedback-link`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        ...body,
        shop_domain: shop
      })
    });
    
    const result = await response.json();
    
    return json(result, { 
      headers: corsHeaders,
      status: response.status 
    });
    
  } catch (error) {
    console.error('Feedback session proxy error:', error);
    return json(
      { 
        success: false, 
        error: error.message 
      }, 
      { 
        headers: corsHeaders,
        status: 500 
      }
    );
  }
}

// Handle GET requests (for testing)
export async function loader({ request }) {
  return json({
    success: true,
    message: "Feedback session proxy endpoint is active",
    method: "POST",
    endpoint: "/a/jarvis-proxy/feedback-session"
  }, {
    headers: corsHeaders
  });
}
