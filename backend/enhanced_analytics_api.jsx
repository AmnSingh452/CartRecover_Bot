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

export async function loader({ request }) {
  try {
    const url = new URL(request.url);
    const shopDomain = url.searchParams.get("shop");
    const days = parseInt(url.searchParams.get("days") || "30");

    if (!shopDomain) {
      return json({ error: "Shop parameter required" }, { status: 400, headers: corsHeaders });
    }

    // Get feedback analytics from your backend
    const feedbackResponse = await fetch(
      `https://cartrecover-bot.onrender.com/api/feedback/analytics/${shopDomain}?days=${days}`
    );

    let feedbackAnalytics = {
      summary: {
        total_feedback: 0,
        average_rating: 0,
        positive_feedback: 0,
        negative_feedback: 0,
        response_rate: "0%"
      },
      recent_feedback: [],
      daily_trends: [],
      topic_breakdown: []
    };

    if (feedbackResponse.ok) {
      const feedbackResult = await feedbackResponse.json();
      if (feedbackResult.success) {
        feedbackAnalytics = feedbackResult.data;
      }
    }

    // Get existing analytics from the original endpoint
    const { PrismaClient } = await import("@prisma/client");
    const prisma = new PrismaClient();

    // Calculate date range
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - days);

    // Get daily metrics for the period
    const dailyMetrics = await prisma.analyticsMetrics.findMany({
      where: {
        shopDomain,
        date: {
          gte: startDate,
          lte: endDate
        }
      },
      orderBy: {
        date: 'asc'
      }
    });

    // Get recent conversations
    const recentConversations = await prisma.chatConversation.findMany({
      where: {
        shopDomain
      },
      orderBy: {
        startTime: 'desc'
      },
      take: 10,
      include: {
        chatMessages: {
          take: 1,
          orderBy: {
            timestamp: 'asc'
          }
        }
      }
    });

    // Get real-time conversation count
    const actualTotalConversations = await prisma.chatConversation.count({
      where: {
        shopDomain,
        startTime: {
          gte: startDate,
          lte: endDate
        }
      }
    });

    // Calculate aggregate metrics
    const metricsConversations = dailyMetrics.reduce((sum, day) => sum + day.totalConversations, 0);
    const totalUniqueVisitors = dailyMetrics.reduce((sum, day) => sum + day.uniqueVisitors, 0);
    const totalConversions = dailyMetrics.reduce((sum, day) => sum + day.conversions, 0);
    const totalRevenue = dailyMetrics.reduce((sum, day) => sum + Number(day.revenue), 0);

    const totalConversations = Math.max(actualTotalConversations, metricsConversations);

    const avgResponseTime = dailyMetrics
      .filter(day => day.averageResponseTime)
      .reduce((sum, day, _, arr) => sum + day.averageResponseTime / arr.length, 0);

    // Use feedback data for customer satisfaction if available
    const avgSatisfaction = feedbackAnalytics.summary.average_rating > 0 
      ? feedbackAnalytics.summary.average_rating 
      : dailyMetrics
          .filter(day => day.customerSatisfaction)
          .reduce((sum, day, _, arr) => sum + day.customerSatisfaction / arr.length, 0);

    // Get top questions from analytics metrics
    const allTopQuestions = [];
    dailyMetrics.forEach(metric => {
      if (metric.topQuestions && Array.isArray(metric.topQuestions)) {
        metric.topQuestions.forEach(q => {
          const existing = allTopQuestions.find(tq => tq.question === q.question);
          if (existing) {
            existing.count += q.count;
          } else {
            allTopQuestions.push({ question: q.question, count: q.count });
          }
        });
      }
    });

    const topQuestions = allTopQuestions
      .sort((a, b) => b.count - a.count)
      .slice(0, 5);

    // Calculate feedback response rate
    const feedbackResponseRate = totalConversations > 0 
      ? ((feedbackAnalytics.summary.total_feedback / totalConversations) * 100).toFixed(1)
      : "0.0";

    const analytics = {
      overview: {
        totalConversations,
        uniqueVisitors: Math.max(totalUniqueVisitors, totalConversations),
        responseRate: totalUniqueVisitors > 0 ? ((totalConversations / totalUniqueVisitors) * 100).toFixed(1) : totalConversations > 0 ? "100.0" : "0",
        avgResponseTime: avgResponseTime > 0 ? avgResponseTime.toFixed(1) : "N/A",
        customerSatisfaction: avgSatisfaction > 0 ? avgSatisfaction.toFixed(1) : "N/A",
        conversionsGenerated: totalConversions,
        revenueGenerated: totalRevenue.toFixed(2),
        // Add feedback metrics
        totalFeedback: feedbackAnalytics.summary.total_feedback,
        feedbackResponseRate: feedbackResponseRate + "%",
        positiveFeedback: feedbackAnalytics.summary.positive_feedback,
        negativeFeedback: feedbackAnalytics.summary.negative_feedback
      },
      timeData: dailyMetrics.map(day => ({
        date: day.date.toISOString().split('T')[0],
        conversations: day.totalConversations,
        conversions: day.conversions,
        revenue: Number(day.revenue)
      })),
      topQuestions,
      recentConversations: recentConversations.map(conv => ({
        id: conv.id,
        customer: conv.customerName || "Anonymous Customer",
        topic: conv.topic || "General",
        timestamp: formatTimeAgo(conv.startTime),
        status: conv.converted ? "Converted" : (conv.status === "completed" ? "Resolved" : "Active"),
        satisfaction: getSatisfactionLabel(conv.customerSatisfaction)
      })),
      // Add feedback analytics section
      feedback: {
        summary: feedbackAnalytics.summary,
        recent: feedbackAnalytics.recent_feedback.map(feedback => ({
          id: feedback.id,
          rating: feedback.rating,
          feedback_text: feedback.feedback_text,
          customer_name: feedback.customer_name || "Anonymous",
          topic: feedback.topic || "General",
          submitted_at: feedback.submitted_at,
          session_id: feedback.session_id
        })),
        dailyTrends: feedbackAnalytics.daily_trends,
        topicBreakdown: feedbackAnalytics.topic_breakdown
      },
      shopDomain,
      dateRange: {
        start: startDate.toISOString().split('T')[0],
        end: endDate.toISOString().split('T')[0]
      }
    };

    return json(analytics, { headers: corsHeaders });

  } catch (error) {
    console.error("Enhanced analytics fetch error:", error);
    return json({ error: "Failed to fetch analytics" }, { status: 500, headers: corsHeaders });
  }
}

// Helper functions remain the same
function formatTimeAgo(date) {
  const now = new Date();
  const diffMs = now - new Date(date);
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffDays > 0) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
  if (diffHours > 0) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  if (diffMins > 0) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
  return 'Just now';
}

function getSatisfactionLabel(rating) {
  if (!rating) return 'Not rated';
  if (rating >= 4.5) return 'Very Positive';
  if (rating >= 3.5) return 'Positive';
  if (rating >= 2.5) return 'Neutral';
  if (rating >= 1.5) return 'Negative';
  return 'Very Negative';
}
