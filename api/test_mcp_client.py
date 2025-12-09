import asyncio
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def run():
    # Define server parameters
    server_params = StdioServerParameters(
        command=sys.executable, # Use the current python interpreter
        args=["fraud_mcp_server.py"],
        env=None
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()

            # List tools
            tools = await session.list_tools()
            print(f"Connected to server. Found {len(tools.tools)} tools:")
            for tool in tools.tools:
                print(f" - {tool.name}: {tool.description}")

            # Test check_police_db
            print("\n--- Testing check_police_db ---")
            result1 = await session.call_tool("check_police_db", arguments={"search_type": "phone", "value": "01012345678"})
            print(f"Result: {result1.content[0].text}")

            # Test check_counterscam
            print("\n--- Testing check_counterscam ---")
            result2 = await session.call_tool("check_counterscam", arguments={"phone_number": "01012345678"})
            print(f"Result: {result2.content[0].text}")

            # Test check_google_safe_browsing (Expect Error due to missing key)
            print("\n--- Testing check_google_safe_browsing ---")
            try:
                result3 = await session.call_tool("check_google_safe_browsing", arguments={"url": "http://google.com"})
                print(f"Result: {result3.content[0].text}")
            except Exception as e:
                print(f"Error: {e}")

            # Test check_virustotal (Expect Error due to missing key)
            print("\n--- Testing check_virustotal ---")
            try:
                result4 = await session.call_tool("check_virustotal", arguments={"url": "http://google.com"})
                print(f"Result: {result4.content[0].text}")
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(run())
