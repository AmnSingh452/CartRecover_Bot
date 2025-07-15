from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()

# Map each shop domain to its size chart (image, HTML, or link)
SIZE_CHARTS = {
    "4ja0wp-y1.myshopify.com": {
        "type": "image",
        "url": "https://wudjuq1w9983po7s-70792740916.shopifypreview.com/pages?preview_key=2383862aada5d4ef9c9d768c89c53794"
    },
    "another-shop.myshopify.com": {
        "type": "html",
        "html": "<table><tr><th>Size</th><th>Bust</th><th>Waist</th></tr><tr><td>S</td><td>34\"</td><td>28\"</td></tr></table>"
    },
    # Add more shops as needed
}

@router.post("/size-chart")
async def get_size_chart(request: Request):
    data = await request.json()
    shop_domain = data.get("shop_domain")
    chart = SIZE_CHARTS.get(shop_domain)
    if chart:
        return JSONResponse({"success": True, "chart": chart})
    else:
        return JSONResponse({"success": False, "message": "No size chart found for this shop."})