import os, re, json, webbrowser, subprocess, wikipedia
from datetime import datetime
from typing import Optional
from constants import SYSTEM_PROMPT
from llm_client import classify_intent, summarize_output, explain_output, chat_completion, generate_search_url
from database import log_command, get_command_history
from extract import execute_command, translate_to_powershell, run_powershell, requires_confirmation
from image_generation_try import ImageGenerator

_image_gen = ImageGenerator()

# Helpers 
def _find_processes(app_name: str) -> str:
    try:
        result = subprocess.run(
            f'tasklist | findstr /I "{app_name}"',
            shell=True, capture_output=True, text=True, timeout=5,
        )
        if result.stdout.strip():
            lines = result.stdout.strip().splitlines()
            entries = []
            for line in lines[:8]:
                parts = line.split()
                if len(parts) >= 2:
                    entries.append(f"• {parts[0]} (PID {parts[1]})")
            return "\n".join(entries)
    except Exception: pass
    return ""

# Main entry point 
def chat_with_llm(
    user_input: str, session_id: str,
    history: list, output_mode: str = "verbose",
    pending_command: Optional[dict] = None,
    last_search_results: Optional[list] = None,
) -> dict:
    # Pending confirmation 
    if pending_command:
        answer = user_input.strip().lower()
        if answer in ("yes", "y", "confirm", "ok", "sure"):
            cmd = pending_command["command"]
            output = execute_command(cmd, skip_confirmation_check=True)
            log_command(session_id, cmd, output, "command")
            return {
                "mode": "command", "confidence": 1.0, "action": cmd,
                "content": f"✅ Executed: `{cmd}`\n\n{output}",
                "raw_output": output, "clear_pending": True, "confidence_val": 1.0,
            }
        return {
            "mode": "chat", "confidence": 1.0, "action": None,
            "content": "❌ Command cancelled.",
            "raw_output": "", "clear_pending": True, "confidence_val": 1.0,
        }
    # Search-result follow-ups
    if last_search_results:
        open_match = re.match(r"open\s+result\s+(\d+)", user_input.lower().strip())
        if open_match:
            idx = int(open_match.group(1)) - 1
            if 0 <= idx < len(last_search_results):
                path = last_search_results[idx]
                os.startfile(path)
                return {
                    "mode": "search", "confidence": 1.0, "action": path,
                    "content": f"📂 Opened: {os.path.basename(path)}",
                    "raw_output": "", "confidence_val": 1.0,
                }
        if re.search(r"delete\s+all\s+\.(\w+)", user_input.lower()):
            m = re.search(r"delete\s+all\s+\.(\w+)", user_input.lower())
            ext = "." + m.group(1)
            to_delete = [f for f in last_search_results if f.endswith(ext)]
            cmd = " & ".join([f'del "{f}"' for f in to_delete[:10]])
            return {
                "mode": "command", "confidence": 0.9, "action": cmd,
                "content": f"⚠️ About to delete {len(to_delete)} {ext} files. Confirm?",
                "raw_output": "", "needs_confirmation": True,
                "pending_command": {"command": cmd, "description": f"delete {len(to_delete)} {ext} files"},
                "confidence_val": 0.9,
            }

    # Session export
    if re.search(r"export\s+(session|chat|history)", user_input, re.IGNORECASE):
        export_path = os.path.join(
            os.path.expanduser("~"), "Desktop",
            f"ARIA_session_{session_id}.md",
        )
        lines = [f"# ARIA Session Export — {session_id}\n"]
        for msg in history:
            lines.append(f"**{msg['role'].upper()}**: {msg['content']}\n")
        try:
            with open(export_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            return {
                "mode": "chat", "confidence": 1.0, "action": export_path,
                "content": f"📄 Session exported to Desktop:\n`{os.path.basename(export_path)}`",
                "raw_output": "", "confidence_val": 1.0,
            }
        except Exception as e:
            return {
                "mode": "chat", "confidence": 1.0, "action": None,
                "content": f"❌ Export failed: {e}",
                "raw_output": "", "confidence_val": 1.0,
            }

    # Intent classification
    intent     = classify_intent(user_input)
    mode       = intent["mode"]
    confidence = intent["confidence"]
    action     = intent.get("action")

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in history[-20:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_input})

    result = {
        "mode": mode, "confidence": confidence, "action": action,
        "content": "", "raw_output": "", "confidence_val": confidence,
    }

    # History
    if mode == "history" or user_input.strip().lower().startswith("/history"):
        items = get_command_history(session_id, 20)
        if not items:
            result["content"] = "📋 No command history for this session."
        else:
            lines = ["📋 **Command History** (last 20):"]
            for i, item in enumerate(items, 1):
                ts = item["timestamp"].strftime("%H:%M:%S") if hasattr(item.get("timestamp", ""), "strftime") else ""
                lines.append(f"  `{i:2d}.` [{ts}] {item['command']}")
            result["content"] = "\n".join(lines)
        result["mode"] = "chat"
        return result

    # Rerun 
    if mode == "rerun" or re.match(r"/rerun\s+\d+", user_input.strip().lower()):
        m = re.search(r"(\d+)", user_input)
        if m:
            idx = int(m.group(1))
            items = get_command_history(session_id, 20)
            if 1 <= idx <= len(items):
                cmd = items[idx - 1]["command"]
                output = execute_command(cmd, skip_confirmation_check=True)
                log_command(session_id, cmd, output, "command")
                result.update({"content": f"🔁 Re-running `{cmd}`\n\n{output}",
                               "mode": "command", "action": cmd, "raw_output": output})
                return result
        result["content"] = "Usage: `/rerun N` where N is the command number from `/history`"
        result["mode"] = "chat"
        return result

    # Image generation 
    if mode == "image_gen" and confidence >= 0.70:
        try:
            safe_name = ImageGenerator.safe_filename(user_input)
            path = os.path.join(os.path.expanduser("~"), "Desktop", f"{safe_name}.png")
            _image_gen.generate(user_input, path)
            result.update({"content": f"🎨 Image generated!\nSaved to Desktop: {safe_name}.png",
                           "mode": "image_gen", "image_path": path})
        except Exception as e:
            result.update({"content": f"❌ Image generation failed: {e}", "mode": "chat"})
        return result

    # Explain 
    if mode == "explain" and confidence >= 0.70:
        subject = action or user_input
        subject = re.sub(r"explain\s+", "", subject, flags=re.IGNORECASE).strip()
        cmd_output = ""
        if re.match(r"^[\w\s|/]+$", subject) and len(subject.split()) <= 3:
            raw = execute_command(subject, skip_confirmation_check=True)
            if not raw.startswith(("❌", "⛔", "__NEEDS")):
                cmd_output = raw
        explanation = explain_output(subject, cmd_output)
        result["content"] = f"📖 **Explanation: {subject}**\n\n{explanation}"
        if cmd_output:
            result["raw_output"] = cmd_output
        return result

    # PowerShell 
    if mode == "powershell" and confidence >= 0.70:
        ps_cmd = translate_to_powershell(action or user_input)
        if not ps_cmd:
            ps_cmd = "Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 10 Name | Format-Table"
        raw_out = run_powershell(ps_cmd)
        log_command(session_id, ps_cmd, raw_out, "powershell")
        display = summarize_output(raw_out) if output_mode == "summary" else raw_out
        result.update({"content": f"⚡ **PowerShell:**\n`{ps_cmd}`\n\n{display}",
                       "raw_output": raw_out, "action": ps_cmd})
        return result

    # Windows command 
    if mode == "command" and confidence >= 0.70:
        if not action:
            cmd_msg = messages + [{"role": "system", "content":
                'Generate Windows command as JSON: {"mode":"command","command":"...","explanation":"..."}'}]
            try:
                raw = chat_completion(cmd_msg, temperature=0.3, max_tokens=256)
                cmd_json = json.loads(raw.replace("```json", "").replace("```", ""))
                action = cmd_json.get("command")
            except Exception:
                pass

        if action:
            kill_match = re.search(r"kill\s+(\w+)", user_input, re.IGNORECASE)
            if kill_match and not re.search(r"taskkill.*?/im\s+\w+", action, re.IGNORECASE):
                procs = _find_processes(kill_match.group(1))
                if procs and "\n" in procs:
                    result["content"] = (f"🔍 Found multiple **{kill_match.group(1)}** processes:\n{procs}\n\n"
                                         "Which PID do you want to kill? (e.g., 'kill PID 1234')")
                    result["needs_followup"] = True
                    return result

            needs_confirm = requires_confirmation(action)
            if needs_confirm:
                result.update({
                    "content": (f"⚠️ This will **{needs_confirm}**.\n"
                                f"Command: `{action}`\n\nType **yes** to confirm or **no** to cancel."),
                    "needs_confirmation": True,
                    "pending_command": {"command": action, "description": needs_confirm},
                })
                return result

            output = execute_command(action, skip_confirmation_check=True)
            log_command(session_id, action, output, "command")
            result["raw_output"] = output
            result["action"] = action

            display_out = summarize_output(output) if output_mode == "summary" else output
            interp_msg = messages + [
                {"role": "assistant", "content": f"Executed: {action}"},
                {"role": "user",      "content": f"Output:\n{display_out}\n\nInterpret briefly."},
            ]
            result["content"] = chat_completion(interp_msg, temperature=0.5, max_tokens=400)
        else:
            result.update({"content": "❌ Could not determine command to execute.", "mode": "chat"})
        return result

    # Wikipedia 
    if mode == "wikipedia" and confidence >= 0.70:
        query = action or user_input
        try:
            summary = wikipedia.summary(query, sentences=3)
            result.update({"content": f"**Wikipedia: {query}**\n\n{summary}", "action": query})
        except wikipedia.exceptions.DisambiguationError as e:
            result["content"] = f"Multiple results found. Be more specific:\n{', '.join(e.options[:5])}"
        except wikipedia.exceptions.PageError:
            result["content"] = f"No Wikipedia page found for '{query}'."
        except Exception as e:
            result["content"] = f"Wikipedia search failed: {e}"
        return result

    # Browser 
    if mode == "browser" and confidence >= 0.70:
        url = action or "https://www.google.com"
        if not url.startswith("http"):
            url = "https://" + url
        webbrowser.open(url)
        result.update({"content": f"🌐 Opened in browser: {url}", "action": url})
        return result

    # Quick open (homepage only — no search query)
    if mode == "quick_open" and confidence >= 0.70:
        action_lower = (action or "").lower()
        quick_links = {
            "youtube":        "https://www.youtube.com/",
            "google":         "https://www.google.com/",
            "stackoverflow":  "https://stackoverflow.com/",
            "stack overflow": "https://stackoverflow.com/",
            "spotify":        "https://www.spotify.com/",
        }
        url = next((link for key, link in quick_links.items() if key in action_lower), None)
        if url:
            webbrowser.open(url)
            result.update({"content": f"🌐 Opened {action}: {url}", "action": url})
        elif "code" in action_lower or "vscode" in action_lower:
            subprocess.Popen("code .", shell=True)
            result["content"] = "💻 Opened Visual Studio Code"
        elif "cmd" in action_lower or "command prompt" in action_lower:
            subprocess.Popen("start cmd", shell=True)
            result["content"] = "⚡ Opened Command Prompt"
        else:
            # Last resort: treat as a smart search rather than failing silently
            resolved = generate_search_url(user_input)
            webbrowser.open(resolved["url"])
            result.update({
                "content": f"🌐 {resolved['explanation']}\n`{resolved['url']}`",
                "action": resolved["url"],
            })
        return result

    # Smart search — site + query → construct URL and open
    if mode == "smart_search" and confidence >= 0.65:
        resolved = generate_search_url(user_input)
        url  = resolved["url"]
        site = resolved["site"]
        expl = resolved["explanation"]
        webbrowser.open(url)
        result.update({
            "content": f"🔍 {expl}\n`{url}`",
            "action":  url,
            "mode":    "smart_search",
        })
        return result

    # Time 
    if mode == "time" and confidence >= 0.70:
        result["content"] = (
            f"🕐 Current time: **{datetime.now().strftime('%H:%M:%S')}**\n"
            f"📅 Date: {datetime.now().strftime('%B %d, %Y')}"
        )
        return result

    # Music 
    if mode == "music" and confidence >= 0.70:
        music_dir = os.path.join(os.path.expanduser("~"), "Music")
        music_files = []
        if os.path.exists(music_dir):
            for root, dirs, files in os.walk(music_dir):
                for file in files:
                    if file.endswith(('.mp3', '.wav', '.m4a', '.flac')):
                        music_files.append(os.path.join(root, file))
                if len(music_files) >= 20:
                    break
        if music_files:
            os.startfile(music_files[0])
            result.update({
                "content": f"🎵 Playing: **{os.path.basename(music_files[0])}**\n\nFound {len(music_files)} songs in Music folder",
                "raw_output": "\n".join([os.path.basename(f) for f in music_files[:10]]),
            })
        else:
            result["content"] = "❌ No music files found in your Music folder"
        return result

    # File search 
    if mode == "search" and confidence >= 0.70:
        extension = action or user_input.replace("search", "").strip()
        if not extension.startswith("."):
            extension = "." + extension
        search_dir = os.path.expanduser("~")
        found_files = []
        for subdir in ["Documents", "Downloads", "Desktop", "Pictures", "Videos"]:
            dir_path = os.path.join(search_dir, subdir)
            if os.path.exists(dir_path):
                for root, dirs, files in os.walk(dir_path):
                    for file in files:
                        if file.endswith(extension):
                            found_files.append(os.path.join(root, file))
                    if len(found_files) >= 50:
                        break
            if len(found_files) >= 50:
                break
        if found_files:
            file_list = "\n".join([f"• {os.path.basename(f)}" for f in found_files[:20]])
            content = f"📁 Found {len(found_files)} files with extension **{extension}**:\n\n{file_list}"
            if len(found_files) > 20:
                content += f"\n\n... and {len(found_files) - 20} more"
            result.update({"content": content,
                           "raw_output": "\n".join(found_files[:50]),
                           "search_results": found_files})
        else:
            result["content"] = f"❌ No files found with extension {extension}"
        return result

    # Show apps 
    if mode == "show_apps" and confidence >= 0.70:
        try:
            cmd_result = subprocess.run(
                ["powershell", "-Command",
                 "Get-WmiObject -Class Win32_Product | Select-Object Name | Format-Table -HideTableHeaders"],
                capture_output=True, text=True, timeout=30,
            )
            if cmd_result.stdout.strip():
                apps = [line.strip() for line in cmd_result.stdout.strip().split("\n") if line.strip()]
                app_list = "\n".join([f"• {app}" for app in apps[:50]])
                content = f"📦 Installed Applications ({len(apps)} found):\n\n{app_list}"
                if len(apps) > 50:
                    content += f"\n\n... and {len(apps) - 50} more"
                result.update({"content": content, "raw_output": "\n".join(apps)})
            else:
                result["content"] = "⚠️ Could not retrieve application list"
        except subprocess.TimeoutExpired:
            result["content"] = "⏱️ Application listing timed out"
        except Exception as e:
            result["content"] = f"❌ Error listing applications: {e}"
        return result

    # Fallback chat
    result["content"] = chat_completion(messages)
    return result