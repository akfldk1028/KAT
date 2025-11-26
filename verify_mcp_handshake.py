import subprocess
import json
import sys
import os
import time

def read_json_rpc_message(process):
    """Reads a JSON-RPC message from stdout by accumulating output."""
    buffer = ""
    start_time = time.time()
    while time.time() - start_time < 5:  # 5 second timeout
        char = process.stdout.read(1)
        if not char:
            break
        buffer += char
        try:
            # Try to parse the buffer as it grows
            # This is a naive approach but works for single JSON objects
            if buffer.strip().startswith("{") and buffer.strip().endswith("}"):
                json.loads(buffer)
                return buffer
        except json.JSONDecodeError:
            continue
    return None

def run_mcp_check():
    # Path to python executable in venv
    python_exe = os.path.join("backend", "venv", "Scripts", "python.exe")
    if not os.path.exists(python_exe):
        print(f"Error: Python executable not found at {python_exe}")
        return

    # Command to run MCP server
    cmd = [python_exe, "-m", "agent.mcp.server"]
    
    # Environment with PYTHONPATH
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()

    print(f"Starting MCP server: {' '.join(cmd)}")
    
    try:
        # Start server process with pipes
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            bufsize=0  # Unbuffered
        )
    except Exception as e:
        print(f"Failed to start process: {e}")
        return

    # 1. Send Initialize Request
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "health-check", "version": "1.0"}
        }
    }
    
    print("Sending initialize request...")
    process.stdin.write(json.dumps(init_request) + "\n")
    process.stdin.flush()

    # Read response
    response_line = read_json_rpc_message(process)
    print(f"Received: {response_line}")
    
    if not response_line:
        print("❌ No response received for initialize")
        process.terminate()
        return

    try:
        response = json.loads(response_line)
        if "result" in response:
            print("✅ Initialize successful!")
        else:
            print("❌ Initialize failed:", response)
            process.terminate()
            return
    except json.JSONDecodeError:
        print("❌ Failed to decode JSON response")
        process.terminate()
        return

    # 2. Send Initialized Notification
    notify_init = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
    }
    process.stdin.write(json.dumps(notify_init) + "\n")
    process.stdin.flush()

    # 3. List Tools
    list_tools_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }
    print("Sending tools/list request...")
    process.stdin.write(json.dumps(list_tools_request) + "\n")
    process.stdin.flush()

    print("Reading tools/list response...")
    response_line = read_json_rpc_message(process)
    print(f"Received raw buffer: {repr(response_line)}")

    if not response_line:
        print("❌ No response received for tools/list")
        process.terminate()
        return

    try:
        response = json.loads(response_line)
        if "result" in response and "tools" in response["result"]:
            tools = response["result"]["tools"]
            tool_names = [t["name"] for t in tools]
            print(f"✅ Tools found: {tool_names}")
            
            expected_tools = ["analyze_outgoing", "analyze_incoming", "analyze_image"]
            if all(t in tool_names for t in expected_tools):
                 print("✅ All expected tools are present.")
            else:
                 print(f"⚠️ Missing tools. Expected {expected_tools}, found {tool_names}")

        else:
            print("❌ List tools failed:", response)
    except json.JSONDecodeError:
        print("❌ Failed to decode JSON response")

    process.terminate()

if __name__ == "__main__":
    run_mcp_check()
