import os
import logging
from core.tool_registry import BaseTool, ToolDefinition, registry
from core.state_guard import guard, Action

logger = logging.getLogger("Delio.NoteTool")

class NoteTool(BaseTool):
    NOTES_DIR = "data/notes"

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="manage_notes",
            description="Manage personal notes. Actions: write, read, list.",
            parameters={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["write", "read", "list"],
                        "description": "The action to perform."
                    },
                    "name": {
                        "type": "string",
                        "description": "The name of the note (filename)."
                    },
                    "content": {
                        "type": "string",
                        "description": "Content of the note (for 'write' action)."
                    }
                },
                "required": ["action"]
            },
            requires_confirmation=False
        )

    async def execute(self, **kwargs) -> str:
        action = kwargs.get("action")
        name = kwargs.get("name")
        content = kwargs.get("content")
        user_id = kwargs.get("user_id")

        if not user_id:
            return "❌ Error: user_id missing."

        # Security check: StateGuard permissions
        try:
            if action in ["read", "list"]:
                await guard.assert_allowed(user_id, Action.FS_READ)
            elif action == "write":
                await guard.assert_allowed(user_id, Action.FS_WRITE)
        except PermissionError as e:
            return f"❌ Security Error: {str(e)}"

        # Ensure directory exists per user
        user_notes_dir = os.path.join(self.NOTES_DIR, str(user_id))
        os.makedirs(user_notes_dir, exist_ok=True)

        if action == "list":
            return self._list_notes(user_notes_dir)
        
        if not name:
            return "❌ Error: 'name' is required for read/write actions."

        # Hardening: Use basename to prevent directory traversal
        safe_name = os.path.basename(name)
        if not safe_name or safe_name in [".", ".."]:
             return "❌ Error: Invalid note name."
        
        # Ensure .txt extension
        if not safe_name.endswith(".txt"):
            safe_name += ".txt"

        file_path = os.path.join(user_notes_dir, safe_name)

        if action == "write":
            if not content:
                return "❌ Error: 'content' is required for write action."
            return self._write_note(file_path, content)
        
        if action == "read":
            return self._read_note(file_path)

        return f"❌ Unknown action '{action}'."

    def _write_note(self, path: str, content: str) -> str:
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"✅ Нотатку '{os.path.basename(path)}' збережено."
        except Exception as e:
            return f"❌ Помилка запису: {str(e)}"

    def _read_note(self, path: str) -> str:
        if not os.path.exists(path):
            return f"❌ Нотатку '{os.path.basename(path)}' не знайдено."
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            return f"📖 **{os.path.basename(path)}**:\n\n{content}"
        except Exception as e:
            return f"❌ Помилка читання: {str(e)}"

    def _list_notes(self, dir_path: str) -> str:
        try:
            files = [f for f in os.listdir(dir_path) if f.endswith(".txt")]
            if not files:
                return "📂 У вас поки немає збережених нотаток."
            
            list_str = "📂 **Ваші нотатки:**\n"
            for f in files:
                list_str += f"- {f.replace('.txt', '')}\n"
            return list_str.strip()
        except Exception as e:
            return f"❌ Помилка отримання списку: {str(e)}"

# Register
registry.register(NoteTool())
