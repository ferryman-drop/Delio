import logging
import os
from states.base import BaseState
from core.state import State
from core.context import ExecutionContext

from core.tool_registry import registry
from core import state_guard

logger = logging.getLogger("Delio.Act")

class ActState(BaseState):
    async def execute(self, context: ExecutionContext) -> State:
        logger.info(f"⚙️ Action phase for user {context.user_id}")
        
        if not context.tool_calls:
            logger.debug("No tool calls to execute.")
            return State.REFLECT

        for tool_call in context.tool_calls:
            tool_name = tool_call.get("name")
            tool_args = tool_call.get("arguments", {})
            
            logger.info(f"🛠️ Executing tool: {tool_name} with args: {tool_args}")
            
            tool = registry.get_tool(tool_name)
            if not tool:
                error_msg = f"Tool '{tool_name}' not found in registry."
                logger.error(error_msg)
                context.tool_outputs.append({"name": tool_name, "error": error_msg})
                continue
                
            try:
                # Inject user_id if not present in args
                if "user_id" not in tool_args and context.user_id:
                    tool_args["user_id"] = context.user_id
                
                result = await tool.execute(**tool_args)
                context.tool_outputs.append({
                    "name": tool_name,
                    "output": result
                })
                logger.info(f"✅ Tool {tool_name} completed.")
                
            except Exception as e:
                logger.exception(f"❌ Failed to execute tool {tool_name}: {e}")
                context.tool_outputs.append({
                    "name": tool_name,
                    "error": str(e)
                })

        return State.REFLECT
