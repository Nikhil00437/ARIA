import os, json, re, urllib.parse, urllib.request
from executor import CommandExecutor

_executor = CommandExecutor()

AVAILABLE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_terminal_command",
            "description": "Execute a command in the system terminal (PowerShell) and return the output.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The command to run (e.g. 'dir', 'ping google.com', 'Get-Process')."
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_url",
            "description": "Open a URL in the default web browser.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to open."
                    }
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a local file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The absolute path to the file to read."
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List the contents of a directory, including files and subdirectories.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory_path": {
                        "type": "string",
                        "description": "Absolute path to the directory to list."
                    }
                },
                "required": ["directory_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_to_file",
            "description": "Create a new file or completely overwrite an existing file with new content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The absolute path to the file to create/overwrite."
                    },
                    "content": {
                        "type": "string",
                        "description": "The full exact string content to write to the file."
                    }
                },
                "required": ["file_path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "replace_file_content",
            "description": "Replace a specific subset of text in an existing file with new text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The absolute path of the target file."
                    },
                    "target_content": {
                        "type": "string",
                        "description": "The exact string segment to be replaced. Must exactly match file contents including all whitespaces."
                    },
                    "replacement_content": {
                        "type": "string",
                        "description": "The content to swap in."
                    }
                },
                "required": ["file_path", "target_content", "replacement_content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Performs a fast web search via DuckDuckGo and returns text snippets holding information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string", 
                        "description": "The web search query."
                    }
                },
                "required": ["query"]
            }
        }
    }
]

def execute_tool(tool_name: str, arguments_json: str) -> str:
    try:
        args = json.loads(arguments_json)
    except json.JSONDecodeError:
        return "Error: Invalid JSON arguments provided."

    if tool_name == "run_terminal_command":
        cmd = args.get("command", "")
        if not cmd:
            return "Error: No command provided."
        success, output = _executor.execute(cmd, use_powershell=True)
        if not output.strip():
            output = "Command executed successfully with no output."
        return f"Exit Code: {'0' if success else '1'}\nOutput:\n{output}"

    elif tool_name == "open_url":
        url = args.get("url", "")
        if not url:
            return "Error: No URL provided."
        success, msg = _executor.open_url(url)
        return msg

    elif tool_name == "read_file":
        path = args.get("file_path", "")
        if not path:
            return "Error: No file path provided."
        try:
            if not os.path.exists(path):
                return f"Error: File '{path}' does not exist."
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                if len(content) > 8000:
                    return content[:8000] + "\n\n...[Truncated: File too large to read entirely]..."
                return content
        except Exception as e: return f"Error reading file: {e}"

    elif tool_name == "list_dir":
        path = args.get("directory_path", "")
        if not path: return "Error: No directory path provided."
        try:
            if not os.path.exists(path): return f"Error: Directory '{path}' does not exist."
            if not os.path.isdir(path): return f"Error: '{path}' is not a directory."
            items = []
            for item in os.listdir(path):
                full = os.path.join(path, item)
                size = os.path.getsize(full) if os.path.isfile(full) else "DIR"
                items.append(f"{item} ({size})")
            return "Directory contents:\n" + "\n".join(items)
        except Exception as e:
            return f"Error listing directory: {e}"

    elif tool_name == "write_to_file":
        path = args.get("file_path", "")
        content = args.get("content", "")
        if not path: return "Error: No file path provided."
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully wrote to '{path}'."
        except Exception as e:
            return f"Error writing file: {e}"

    elif tool_name == "replace_file_content":
        path = args.get("file_path", "")
        target = args.get("target_content", "")
        replacement = args.get("replacement_content", "")
        if not path: return "Error: No file path provided."
        try:
            if not os.path.exists(path): return f"Error: File '{path}' does not exist."
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            if target not in content:
                return "Error: Target content not found in file. Ensure exact matching including whitespace."
            new_content = content.replace(target, replacement)
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
            return f"Successfully updated '{path}'."
        except Exception as e:
            return f"Error updating file: {e}"

    elif tool_name == "search_web":
        query = args.get("query", "")
        if not query: return "Error: No query provided."
        try:
            url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req) as response:
                html = response.read().decode('utf-8')
            # Extract basic result snippets
            snippets = re.findall(r'<a class="result__snippet[^>]*>(.*?)</a>', html, re.IGNORECASE | re.DOTALL)
            clean_snippets = [re.sub(r'<[^>]+>', '', s).strip() for s in snippets]
            if clean_snippets:
                return "Search results snippets:\n" + "\n\n".join(f"- {s}" for s in clean_snippets[:5])
            return "No useful snippets found."
        except Exception as e:
            return f"Error searching web: {e}"

    else:
        return f"Error: Unknown tool '{tool_name}'."
