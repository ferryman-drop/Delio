import asyncio
import re
import io
import sys
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_systemic")

# Mock Tools Environment
class MockTools:
    def search_web(self, query):
        return f"Results for {query}: Bitcoin is $100k"

tools = MockTools()
user_id = 12345

async def test_deepseek_parsing_logic():
    logger.info("Testing DeepSeek Tool Parsing Logic...")
    
    # 1. Simulate DeepSeek Response
    content = """
I will check the price.
<tool_code>
print(tools.search_web("Bitcoin price"))
</tool_code>
"""
    
    # 2. Parse and Execute Logic (Copied from main.py for unit testing)
    if "<tool_code>" in content:
        code_match = re.search(r"<tool_code>(.*?)</tool_code>", content, re.DOTALL)
        if code_match:
            code = code_match.group(1).strip()
            logger.info(f"Found Code: {code}")
            
            # Exec
            local_env = {"tools": tools, "user_id": user_id}
            
            # Capture stdout
            old_stdout = sys.stdout
            redir_out = io.StringIO()
            sys.stdout = redir_out
            
            try:
                exec(code, {}, local_env)
                output = redir_out.getvalue().strip()
            except Exception as e:
                output = f"Error: {e}"
            finally:
                sys.stdout = old_stdout
            
            logger.info(f"Execution Output: {output}")
            
            assert "Bitcoin is $100k" in output
            logger.info("✅ Tool execution successful")
            return

    logger.error("❌ Tool execution failed (code not found or executed)")

async def test_scheduler_init():
    logger.info("Testing Scheduler Init...")
    try:
        import scheduler
        scheduler.init_scheduler()
        # Check if job exists
        jobs = scheduler.scheduler.get_jobs()
        assert len(jobs) >= 2, "Jobs not added"
        logger.info(f"✅ Scheduler initialized with {len(jobs)} jobs")
        scheduler.scheduler.shutdown()
    except Exception as e:
        logger.error(f"❌ Scheduler test failed: {e}")

async def main():
    await test_deepseek_parsing_logic()
    await test_scheduler_init()

if __name__ == "__main__":
    asyncio.run(main())
