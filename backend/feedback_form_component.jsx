import { json, redirect } from "@remix-run/node";
import { useLoaderData, Form, useActionData, useNavigation } from "@remix-run/react";
import { useState } from "react";

// CORS headers
const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
};

// Handle OPTIONS preflight requests
export async function options() {
  return new Response(null, {
    status: 200,
    headers: corsHeaders
  });
}

export async function loader({ params }) {
  const { feedbackToken } = params;
  
  if (!feedbackToken) {
    throw new Response("Feedback token is required", { status: 400 });
  }

  try {
    // Get feedback session details from your backend
    const response = await fetch(`https://cartrecover-bot.onrender.com/api/feedback/token/${feedbackToken}`);
    
    if (!response.ok) {
      if (response.status === 404) {
        throw new Response("Feedback link expired or not found", { status: 404 });
      }
      throw new Response("Failed to load feedback session", { status: 500 });
    }
    
    const result = await response.json();
    
    if (!result.success) {
      throw new Response(result.message || "Invalid feedback session", { status: 400 });
    }
    
    return json({
      feedbackToken,
      sessionData: result.data
    }, { headers: corsHeaders });
    
  } catch (error) {
    console.error("Feedback loader error:", error);
    throw new Response("Failed to load feedback form", { status: 500 });
  }
}

export async function action({ request, params }) {
  const { feedbackToken } = params;
  const formData = await request.formData();
  
  const rating = parseInt(formData.get("rating"));
  const feedbackText = formData.get("feedback_text");
  const customerName = formData.get("customer_name");
  const customerEmail = formData.get("customer_email");
  
  // Get session data first
  const sessionResponse = await fetch(`https://cartrecover-bot.onrender.com/api/feedback/token/${feedbackToken}`);
  if (!sessionResponse.ok) {
    return json({ 
      error: "Invalid or expired feedback link" 
    }, { status: 400, headers: corsHeaders });
  }
  
  const sessionResult = await sessionResponse.json();
  const sessionData = sessionResult.data;
  
  try {
    // Submit feedback to your backend
    const response = await fetch("https://cartrecover-bot.onrender.com/api/feedback/submit", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        session_id: sessionData.session_id,
        shop_domain: sessionData.shop_domain,
        rating,
        feedback_text: feedbackText,
        customer_name: customerName,
        customer_email: customerEmail,
        conversation_topic: "General" // You can enhance this based on session data
      })
    });
    
    const result = await response.json();
    
    if (result.success) {
      return json({ 
        success: true, 
        message: "Thank you for your feedback!" 
      }, { headers: corsHeaders });
    } else {
      return json({ 
        error: result.message || "Failed to submit feedback" 
      }, { headers: corsHeaders });
    }
    
  } catch (error) {
    console.error("Feedback submission error:", error);
    return json({ 
      error: "Failed to submit feedback. Please try again." 
    }, { headers: corsHeaders });
  }
}

export default function FeedbackForm() {
  const { feedbackToken, sessionData } = useLoaderData();
  const actionData = useActionData();
  const navigation = useNavigation();
  const [selectedRating, setSelectedRating] = useState(0);

  const isSubmitting = navigation.state === "submitting";

  // If feedback was successfully submitted, show thank you message
  if (actionData?.success) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-6 text-center">
          <div className="text-6xl mb-4">🎉</div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Thank You!</h2>
          <p className="text-gray-600 mb-4">
            Your feedback has been submitted successfully. We appreciate you taking the time to help us improve!
          </p>
          <div className="text-green-600 font-medium">
            ✅ {actionData.message}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="max-w-lg w-full bg-white rounded-lg shadow-lg p-6">
        <div className="text-center mb-6">
          <div className="text-4xl mb-2">💬</div>
          <h1 className="text-2xl font-bold text-gray-900">How was your chat experience?</h1>
          <p className="text-gray-600 mt-2">
            Your feedback helps us improve our AI assistant
          </p>
        </div>

        {actionData?.error && (
          <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
            {actionData.error}
          </div>
        )}

        <Form method="post" className="space-y-6">
          {/* Rating Stars */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-3">
              Overall Rating *
            </label>
            <div className="flex justify-center space-x-1">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  type="button"
                  onClick={() => setSelectedRating(star)}
                  className="text-3xl focus:outline-none transition-colors"
                >
                  <span className={star <= selectedRating ? "text-yellow-400" : "text-gray-300"}>
                    ⭐
                  </span>
                </button>
              ))}
            </div>
            <input
              type="hidden"
              name="rating"
              value={selectedRating}
              required
            />
            {selectedRating > 0 && (
              <p className="text-center text-sm text-gray-600 mt-2">
                {selectedRating === 1 && "Very Poor"}
                {selectedRating === 2 && "Poor"}
                {selectedRating === 3 && "Average"}
                {selectedRating === 4 && "Good"}
                {selectedRating === 5 && "Excellent"}
              </p>
            )}
          </div>

          {/* Feedback Text */}
          <div>
            <label htmlFor="feedback_text" className="block text-sm font-medium text-gray-700 mb-2">
              Tell us more about your experience (optional)
            </label>
            <textarea
              id="feedback_text"
              name="feedback_text"
              rows={4}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="What did you like or dislike? How can we improve?"
            />
          </div>

          {/* Customer Information */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="customer_name" className="block text-sm font-medium text-gray-700 mb-2">
                Your Name (optional)
              </label>
              <input
                type="text"
                id="customer_name"
                name="customer_name"
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="John Doe"
              />
            </div>
            <div>
              <label htmlFor="customer_email" className="block text-sm font-medium text-gray-700 mb-2">
                Email (optional)
              </label>
              <input
                type="email"
                id="customer_email"
                name="customer_email"
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="john@example.com"
              />
            </div>
          </div>

          {/* Submit Button */}
          <div className="text-center">
            <button
              type="submit"
              disabled={selectedRating === 0 || isSubmitting}
              className="w-full bg-blue-600 text-white py-3 px-6 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:bg-gray-400 disabled:cursor-not-allowed font-medium transition-colors"
            >
              {isSubmitting ? "Submitting..." : "Submit Feedback"}
            </button>
          </div>

          {selectedRating === 0 && (
            <p className="text-sm text-gray-500 text-center">
              Please select a rating to submit your feedback
            </p>
          )}
        </Form>

        {/* Session Info (for debugging, can be removed in production) */}
        <div className="mt-6 pt-4 border-t border-gray-200 text-xs text-gray-500">
          <p>Session: {sessionData.session_id}</p>
          <p>Shop: {sessionData.shop_domain}</p>
        </div>
      </div>
    </div>
  );
}

export function ErrorBoundary({ error }) {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-6 text-center">
        <div className="text-6xl mb-4">😕</div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Oops!</h2>
        <p className="text-gray-600 mb-4">
          {error.status === 404 
            ? "This feedback link has expired or is no longer valid."
            : "Something went wrong loading the feedback form."
          }
        </p>
        <p className="text-sm text-gray-500">
          Please contact support if you continue to have issues.
        </p>
      </div>
    </div>
  );
}
