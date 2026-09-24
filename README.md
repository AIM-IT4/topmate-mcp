# Topmate MCP

Read-only MCP server for the public Topmate profile:

https://topmate.io/amit_kumar_jha

## Production tools

- `topmate_get_profile`
- `topmate_list_services`
- `topmate_mcp_status`

The deployment uses the official Python MCP SDK v2 high-level `MCPServer` API with stateless Streamable HTTP and JSON responses, suitable for serverless runtimes.

## Deploy to Vercel

[Deploy to Vercel](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2FAIM-IT4%2Ftopmate-mcp)

After deployment:

- Health check: `https://<your-project>.vercel.app/health`
- MCP endpoint: `https://<your-project>.vercel.app/mcp`

Private Gmail/Calendar tools are intentionally not enabled on the public endpoint yet. Add authentication before enabling them.
