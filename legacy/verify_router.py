import logging
from unittest.mock import MagicMock

# Mock OpenAI client before importing router
import sys
from types import ModuleType

# Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_router")

def test_router():
    import router
    
    # Mocking router instance manually since we don't have API key in env potentially
    router.router_instance.client = MagicMock()
    
    # Mock Response
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = '{"complexity": "HIGH", "recommended_model": "pro", "reason": "Life Strategy", "optimized_context": "User needs strategic advice."}'
    router.router_instance.client.chat.completions.create.return_value = mock_resp
    
    # Run
    decision = router.route("What should I do with my life?")
    
    logger.info(f"Decision: {decision}")
    
    assert decision["complexity"] == "HIGH"
    assert decision["recommended_model"] == "pro"
    
    logger.info("✅ Router logic verified")

if __name__ == "__main__":
    test_router()
