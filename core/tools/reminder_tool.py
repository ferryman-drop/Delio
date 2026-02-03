import logging
import re
from datetime import datetime, timedelta
from core.tool_registry import BaseTool, ToolDefinition, registry
from scheduler import scheduler, bot_instance
from core.state_guard import guard, Action

logger = logging.getLogger("Delio.ReminderTool")

class ReminderTool(BaseTool):
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="set_reminder",
            description="Set a reminder for the user. Supports ISO format or relative delay like '10 minutes'.",
            parameters={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The message to remind the user about."
                    },
                    "time_str": {
                        "type": "string",
                        "description": "Time to remind. Format: ISO date (YYYY-MM-DD HH:MM:SS) or 'X minutes/hours/days'."
                    }
                },
                "required": ["text", "time_str"]
            },
            requires_confirmation=False
        )

    async def execute(self, **kwargs) -> str:
        text = kwargs.get("text")
        time_str = kwargs.get("time_str")
        user_id = kwargs.get("user_id")

        if not user_id:
            return "❌ Error: user_id missing."

        # Security check: StateGuard permissions
        try:
            await guard.assert_allowed(user_id, Action.NETWORK)
        except PermissionError as e:
            return f"❌ Security Error: {str(e)}"

        target_time = self._parse_time(time_str)
        if not target_time:
            return f"❌ Error: Could not parse time '{time_str}'. Use ISO format or 'X minutes/hours/days'."

        if target_time <= datetime.now():
            return "❌ Error: Reminder time must be in the future."

        # Schedule the job
        try:
            scheduler.add_job(
                self._send_notification,
                'date',
                run_date=target_time,
                args=[user_id, text],
                id=f"reminder_{user_id}_{target_time.timestamp()}",
                replace_existing=True
            )
            return f"✅ Нагадування встановлено на {target_time.strftime('%Y-%m-%d %H:%M:%S')}."
        except Exception as e:
            logger.error(f"Failed to schedule reminder: {e}")
            return f"❌ Помилка планування: {str(e)}"

    async def _send_notification(self, user_id: int, text: str):
        """Callback to send the actually message"""
        if bot_instance:
            try:
                msg = f"🔔 **Нагадування:**\n{text}"
                await bot_instance.send_message(user_id, msg)
                logger.info(f"🔔 Reminder sent to {user_id}")
            except Exception as e:
                logger.error(f"Failed to send reminder message to {user_id}: {e}")
        else:
            logger.warning("⚠️ Bot instance not set in scheduler, cannot send reminder notification.")

    def _parse_time(self, t_str: str) -> datetime:
        """Simple parser for ISO or relative time"""
        t_str = t_str.strip().lower()
        
        # 1. ISO format check
        try:
            return datetime.fromisoformat(t_str)
        except ValueError:
            pass

        # 2. Relative time check: "X minutes", "Y hours", "Z days"
        match = re.match(r"(\d+)\s*(minute|min|hour|hr|day|d)s?", t_str)
        if match:
            value = int(match.group(1))
            unit = match.group(2)
            
            if unit.startswith('min'):
                return datetime.now() + timedelta(minutes=value)
            elif unit.startswith('h'):
                return datetime.now() + timedelta(hours=value)
            elif unit.startswith('d'):
                return datetime.now() + timedelta(days=value)
        
        return None

# Register
registry.register(ReminderTool())
