
import sys
import logging
sys.path.append('/root/ai_assistant')

from tools import search_web, execute_python

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestTools")

def test_search():
    """Test web search functionality"""
    logger.info("🧪 Testing Web Search...")
    
    # Test 1: Normal search
    result = search_web("Python 3.12 release date", max_results=3)
    if "October 2023" in result or "2023" in result:
        logger.info("✅ Search Test 1 PASSED (Python release date)")
    else:
        logger.warning(f"⚠️ Search Test 1 inconclusive: {result[:100]}")
    
    # Test 2: Empty query handling
    result2 = search_web("")
    if "❌" in result2 or "error" in result2.lower():
        logger.info("✅ Search Test 2 PASSED (empty query)")
    else:
        logger.warning("⚠️ Search Test 2 failed: should handle empty query")
    
    print("\n" + "="*50)
    print("SEARCH RESULTS SAMPLE:")
    print("="*50)
    print(result[:500])
    print("="*50 + "\n")

def test_execution():
    """Test Python code execution"""
    logger.info("🧪 Testing Python Execution...")
    
    # Test 1: Simple calculation
    result = execute_python("print(2 + 2)")
    if "4" in result:
        logger.info("✅ Execution Test 1 PASSED (simple math)")
    else:
        logger.error(f"❌ Execution Test 1 FAILED: {result}")
    
    # Test 2: Loop and sum
    code = """
total = sum([1, 2, 3, 4, 5])
print(f"Sum: {total}")
"""
    result2 = execute_python(code)
    if "15" in result2:
        logger.info("✅ Execution Test 2 PASSED (list sum)")
    else:
        logger.error(f"❌ Execution Test 2 FAILED: {result2}")
    
    # Test 3: Restricted access (should fail safely)
    result3 = execute_python("import os; os.system('ls')")
    if "❌" in result3 or "Помилка" in result3:
        logger.info("✅ Execution Test 3 PASSED (restricted import blocked)")
    else:
        logger.warning(f"⚠️ Execution Test 3: {result3}")
    
    # Test 4: Math module (should work)
    result4 = execute_python("import math; print(math.pi)")
    if "3.14" in result4:
        logger.info("✅ Execution Test 4 PASSED (math module allowed)")
    else:
        logger.warning(f"⚠️ Execution Test 4: {result4}")
    
    print("\n" + "="*50)
    print("EXECUTION RESULTS SAMPLES:")
    print("="*50)
    print(f"Test 1: {result}")
    print(f"Test 2: {result2}")
    print(f"Test 3 (restricted): {result3}")
    print(f"Test 4 (math): {result4}")
    print("="*50 + "\n")

if __name__ == "__main__":
    logger.info("--- STARTING TOOLS TEST ---")
    test_search()
    test_execution()
    logger.info("--- TOOLS TEST COMPLETE ---")
