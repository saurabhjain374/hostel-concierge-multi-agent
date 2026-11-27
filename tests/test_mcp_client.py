
import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    # Configure how the MCP server should be started
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "src.mcp_server.server"]
    )

    # Start server and establish an MCP client connection
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:

            # Initialize the MCP connection
            await session.initialize()

            # Discover available tools
            tools_result = await session.list_tools()

            print("\nAvailable MCP tools:")
            for tool in tools_result.tools:
                print(f"- {tool.name}: {tool.description}")

            # Invoke the booking tool
            print("\nCalling get_guest_booking for G001...")

            result = await session.call_tool(
                "get_guest_booking",
                arguments={"guest_id": "G001"}
            )

            print("\nTool response:")
            for content in result.content:
                if content.type == "text":
                    print(content.text)


if __name__ == "__main__":
    asyncio.run(main())
