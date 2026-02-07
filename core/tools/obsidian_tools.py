import os
import logging
import datetime
from core.tool_registry import BaseTool, ToolDefinition, registry
from core.state_guard import guard, Action

logger = logging.getLogger("Delio.ObsidianTool")

class ObsidianTool(BaseTool):
    OBSIDIAN_ROOT = "/data/obsidian"

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="obsidian",
            description="Manage Obsidian notes (Second Brain). Actions: create, append, read.",
            parameters={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["create", "append", "read"],
                        "description": "The action: 'create' (new note), 'append' (add to end), 'read'."
                    },
                    "filename": {
                        "type": "string",
                        "description": "Filename (e.g., 'Daily Log.md'). If no extension, .md is added."
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write or append."
                    },
                    "folder": {
                        "type": "string",
                        "description": "Folder relative to root (default: 'Inbox'). Only for 'create'."
                    }
                },
                "required": ["action", "filename"]
            },
            requires_confirmation=False
        )

    async def execute(self, **kwargs) -> str:
        action = kwargs.get("action")
        filename = kwargs.get("filename")
        content = kwargs.get("content")
        folder = kwargs.get("folder", "Inbox")
        user_id = kwargs.get("user_id")

        if not user_id:
            return "❌ Error: user_id missing."

        # Security Checks
        try:
            if action == "read":
                await guard.assert_allowed(user_id, Action.FS_READ)
            elif action in ["create", "append"]:
                await guard.assert_allowed(user_id, Action.FS_WRITE)
        except PermissionError as e:
            return f"❌ Security Error: {str(e)}"

        # Validate Path
        if not filename:
            return "❌ Error: Filename required."
        
        # Helper to sanitise path
        safe_name = os.path.basename(filename)
        if not safe_name.endswith(".md"):
            safe_name += ".md"
            
        if action == "create":
            # Prevent directory traversal in folder
            safe_folder = folder.replace("..", "").strip("/")
            full_dir = os.path.realpath(os.path.join(self.OBSIDIAN_ROOT, safe_folder))
            if not full_dir.startswith(os.path.realpath(self.OBSIDIAN_ROOT)):
                return f"❌ Security Error: Path traversal detected in folder '{folder}'."
            os.makedirs(full_dir, exist_ok=True)

            file_path = os.path.join(full_dir, safe_name)
            
            if os.path.exists(file_path):
                return f"❌ Error: Note '{safe_name}' already exists. Use 'append'?"
                
            if not content:
                content = "# " + safe_name.replace(".md", "")
            
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                return f"✅ Created note: [[{safe_name}]] in {safe_folder}"
            except Exception as e:
                return f"❌ Write failed: {e}"

        elif action == "append":
            # Search for file in Root or subfolders? 
            # For v1: specific logic. We try to find it. If not found, fail.
            # Simplified: Look in Root and Inbox
            found_path = None
            for root, dirs, files in os.walk(self.OBSIDIAN_ROOT):
                if safe_name in files:
                    found_path = os.path.join(root, safe_name)
                    break
            
            if not found_path:
                 # Fallback: Create in Inbox if content provided?
                 # No, strict.
                 return f"❌ Error: Note '{safe_name}' not found in Vault."
            
            if not content:
                 return "❌ Error: Content required for append."

            timestamp = datetime.datetime.now().strftime("%H:%M")
            append_text = f"\n\n### Update ({timestamp})\n{content}"
            
            try:
                with open(found_path, "a", encoding="utf-8") as f:
                    f.write(append_text)
                return f"✅ Appended to [[{safe_name}]]"
            except Exception as e:
                return f"❌ Append failed: {e}"

        elif action == "read":
            found_path = None
            for root, dirs, files in os.walk(self.OBSIDIAN_ROOT):
                if safe_name in files:
                    found_path = os.path.join(root, safe_name)
                    break
            
            if not found_path:
                return f"❌ Note '{safe_name}' not found."
            
            try:
                with open(found_path, "r", encoding="utf-8") as f:
                    data = f.read()
                return f"📄 **{safe_name}**:\n\n{data}"
            except Exception as e:
                return f"❌ Read failed: {e}"

        return f"❌ Unknown action {action}"

# Register
registry.register(ObsidianTool())
