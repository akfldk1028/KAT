import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

try:
    from agent.mcp.tools import mcp
    print("✅ Successfully imported 'mcp' object.")
    
    # FastMCP stores tools in _tools or similar. Let's inspect.
    # Note: Internal API might vary, but we can check if the object exists.
    print(f"MCP Object: {mcp}")
    print(f"MCP Name: {mcp.name}")
    
    # Check if tools are registered (FastMCP usually uses decorators)
    # We can't easily list them without private API access, but successful import 
    # and object existence is a strong signal.
    
    # Try to find the tool functions in the module
    from agent.mcp import tools
    expected_tools = ["analyze_outgoing", "analyze_incoming", "analyze_image"]
    found_tools = []
    for t in expected_tools:
        if hasattr(tools, t):
            found_tools.append(t)
    
    print(f"Found tool functions: {found_tools}")
    
    if len(found_tools) == 3:
        print("✅ All tool functions are present in the module.")
    else:
        print("❌ Missing tool functions.")

except ImportError as e:
    print(f"❌ ImportError: {e}")
except Exception as e:
    print(f"❌ Error: {e}")
