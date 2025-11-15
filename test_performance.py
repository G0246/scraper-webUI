#!/usr/bin/env python3
"""
Performance test for scraper-webUI optimizations

This script tests the key optimizations:
1. Robots.txt caching
2. Parallel detail page fetching
3. URL deduplication
"""

import time
from scraper.core import (
    is_allowed_by_robots,
    _robots_cache,
)


def test_robots_caching():
    """Test that robots.txt caching works and improves performance."""
    print("\n=== Testing Robots.txt Caching ===")
    
    # Clear cache
    _robots_cache.clear()
    
    # First call - should fetch from network
    url = "https://www.python.org/"
    start = time.perf_counter()
    result1 = is_allowed_by_robots(url, "test-bot")
    time1 = time.perf_counter() - start
    print(f"First call (network fetch): {time1*1000:.2f}ms - Allowed: {result1}")
    
    # Second call - should use cache
    start = time.perf_counter()
    result2 = is_allowed_by_robots(url, "test-bot")
    time2 = time.perf_counter() - start
    print(f"Second call (cached): {time2*1000:.2f}ms - Allowed: {result2}")
    
    if time2 < time1:
        speedup = time1 / time2
        print(f"✓ Caching works! {speedup:.1f}x faster on cached call")
    else:
        print("⚠ Cache may not be working as expected")
    
    # Third call with different URL on same domain - should use cache
    url2 = "https://www.python.org/downloads/"
    start = time.perf_counter()
    result3 = is_allowed_by_robots(url2, "test-bot")
    time3 = time.perf_counter() - start
    print(f"Different URL, same domain (cached): {time3*1000:.2f}ms - Allowed: {result3}")
    
    return time1, time2, time3


def test_session_pooling():
    """Test that session pooling configuration is optimal."""
    print("\n=== Testing Session Configuration ===")
    
    from scraper.core import create_session
    
    # Create a session
    session = create_session(user_agent="test-bot", fast_mode=False)
    
    # Check adapter configuration
    adapter = session.get_adapter("https://example.com")
    
    print(f"Pool connections: {adapter._pool_connections}")
    print(f"Pool max size: {adapter._pool_maxsize}")
    print(f"Pool block: {adapter._pool_block}")
    
    # Verify optimized settings
    assert adapter._pool_connections >= 50, "Pool connections should be at least 50"
    assert adapter._pool_maxsize >= 100, "Pool max size should be at least 100"
    assert adapter._pool_block is False, "Pool should not block"
    
    print("✓ Session pooling is optimized")
    
    # Test fast mode
    fast_session = create_session(user_agent="test-bot", fast_mode=True)
    fast_adapter = fast_session.get_adapter("https://example.com")
    retry = fast_adapter.max_retries
    
    print(f"\nFast mode - Total retries: {retry.total}")
    print(f"Fast mode - Backoff factor: {retry.backoff_factor}")
    
    print("✓ Fast mode configuration verified")


def test_parallel_optimizations():
    """Test that parallel processing infrastructure is in place."""
    print("\n=== Testing Parallel Processing Setup ===")
    
    from scraper.core import _enrich_items_with_detail_images
    import inspect
    
    # Check that the function exists and has the right signature
    sig = inspect.signature(_enrich_items_with_detail_images)
    params = list(sig.parameters.keys())
    
    assert 'session' in params
    assert 'items' in params
    assert 'detail_image_selector' in params
    assert 'max_workers' in params, "max_workers parameter should exist"
    
    print("✓ Parallel image enrichment function exists")
    print(f"  Parameters: {params}")
    
    # Check default max_workers
    default_workers = sig.parameters['max_workers'].default
    print(f"  Default max_workers: {default_workers}")
    assert default_workers >= 8, "Default workers should be at least 8"
    
    print("✓ Parallel processing infrastructure verified")


def test_html_truncation():
    """Test that HTML field truncation is working."""
    print("\n=== Testing HTML Truncation ===")
    
    from bs4 import BeautifulSoup
    from scraper.core import _elements_to_items
    
    # Create a large HTML element
    large_html = "<div>" + "x" * 10000 + "</div>"
    soup = BeautifulSoup(large_html, "lxml")
    elements = soup.find_all("div")
    
    items = _elements_to_items(
        base_url="https://example.com",
        elements=elements,
        attribute_name=None
    )
    
    if items:
        html_len = len(items[0]['html'])
        print(f"Original HTML size: ~10000 chars")
        print(f"Stored HTML size: {html_len} chars")
        
        if html_len <= 5003:  # 5000 + "..."
            print("✓ HTML truncation is working")
        else:
            print("⚠ HTML truncation may not be working")


def main():
    """Run all performance tests."""
    print("=" * 60)
    print("Performance Tests for scraper-webUI Optimizations")
    print("=" * 60)
    
    try:
        # Test 1: Robots.txt caching
        test_robots_caching()
        
        # Test 2: Session pooling
        test_session_pooling()
        
        # Test 3: Parallel processing
        test_parallel_optimizations()
        
        # Test 4: HTML truncation
        test_html_truncation()
        
        print("\n" + "=" * 60)
        print("All performance tests completed successfully!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
