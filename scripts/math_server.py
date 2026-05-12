"""示例 MCP 服务器 — 提供数学计算工具，用于测试 MCP 集成。"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Math")


@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b


@mcp.tool()
def multiply(a: int, b: int) -> int:
    """Multiply two numbers together."""
    return a * b


if __name__ == "__main__":
    mcp.run(transport="stdio")
