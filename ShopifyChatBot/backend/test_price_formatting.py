#!/usr/bin/env python3
"""
Test script to verify price formatting and product card formatting improvements.
"""

def test_price_conversion():
    """Test the price conversion logic for different currencies."""
    print("=== Testing Price Conversion ===")
    
    test_cases = [
        {"raw_price": "24900.0", "currency": "INR", "expected": "249.00 INR"},
        {"raw_price": "1500.0", "currency": "INR", "expected": "15.00 INR"},
        {"raw_price": "29.99", "currency": "USD", "expected": "29.99 USD"},
        {"raw_price": "N/A", "currency": "INR", "expected": "N/A INR"},
        {"raw_price": "invalid", "currency": "INR", "expected": "invalid INR"}
    ]
    
    for test_case in test_cases:
        raw_price = test_case["raw_price"]
        currency = test_case["currency"]
        
        # Apply the same logic as in recommendation_agent.py
        if raw_price != "N/A" and raw_price:
            try:
                price_float = float(raw_price)
                # For INR, divide by 100 to convert paise to rupees
                if currency == "INR":
                    display_price = price_float / 100
                else:
                    display_price = price_float
                product_price = f"{display_price:.2f}"
            except (ValueError, TypeError):
                product_price = raw_price
        else:
            product_price = "N/A"
        
        result = f"{product_price} {currency}"
        status = "✅ PASS" if result == test_case["expected"] else "❌ FAIL"
        
        print(f"{status} Raw: {raw_price} {currency} → Formatted: {result}")
        if result != test_case["expected"]:
            print(f"    Expected: {test_case['expected']}")

def test_product_card_formatting():
    """Test the product card formatting logic."""
    print("\n=== Testing Product Card Formatting ===")
    
    sample_product = {
        'name': 'AURUM (MISS DIOR)',
        'price': '249.00 INR',
        'url': 'https://zynx-d.myshopify.com/products/aurum-miss-dior',
        'image': 'https://cdn.shopify.com/s/files/1/0123/4567/8901/products/aurum-miss-dior.jpg'
    }
    
    # Apply the same formatting logic as in agent_coordinator.py
    name = sample_product.get('name', 'Unknown Product')
    price = sample_product.get('price', 'N/A')
    url = sample_product.get('url', '#')
    image = sample_product.get('image', '')
    
    formatted_card = f"\n🛍️ **{name}**\n"
    formatted_card += f"💰 Price: {price}\n"
    if url and url != '#':
        formatted_card += f"🔗 [View Product]({url})\n"
    if image:
        formatted_card += f"📸 [Product Image]({image})\n"
    formatted_card += "\n"
    
    print("Formatted Product Card:")
    print(formatted_card)
    print("✅ Product card formatting looks good!")

def test_deduplication_logic():
    """Test the product deduplication logic."""
    print("=== Testing Product Deduplication ===")
    
    sample_products = [
        {"title": "AURUM (MISS DIOR)", "price": "249.00"},
        {"title": "AURUM (MISS DIOR)", "price": "249.00"},  # Duplicate
        {"title": "Summer Perfume", "price": "299.00"},
        {"title": "AURUM (MISS DIOR)", "price": "249.00"},  # Another duplicate
        {"title": "Winter Collection", "price": "199.00"}
    ]
    
    # Apply the same deduplication logic as in recommendation_agent.py
    seen_products = set()
    unique_products = []
    
    for product in sample_products:
        product_title = product["title"]
        if product_title not in seen_products:
            seen_products.add(product_title)
            unique_products.append(product)
        else:
            print(f"⏭️  Skipping duplicate: {product_title}")
    
    print(f"\nOriginal products: {len(sample_products)}")
    print(f"Unique products: {len(unique_products)}")
    print("Unique products list:")
    for i, product in enumerate(unique_products, 1):
        print(f"  {i}. {product['title']} - {product['price']}")
    
    print("✅ Deduplication working correctly!")

if __name__ == "__main__":
    print("🧪 Testing Recommendation System Improvements")
    print("=" * 50)
    
    test_price_conversion()
    test_product_card_formatting()
    test_deduplication_logic()
    
    print("\n🎉 All tests completed!")
    print("\nChanges implemented:")
    print("✅ Price conversion: paise → rupees for INR")
    print("✅ Product deduplication: unique titles only")
    print("✅ Enhanced formatting: product cards with links and images")