# Installing Kyrodata (for coding agents)

Kyrodata is a **remote** MCP server. Do **not** clone, build, or run anything from this
repository — there is no server code here. Setup is one config block plus a key.

## Steps

1. **Ask the user for their Kyrodata API key.** It starts with `kd_live_`. If they do not
   have one, point them at https://kyrodata.com/user/api-keys — the key is shown once, at
   creation. Do not proceed without it: the server answers `401` to every unauthenticated
   call and there is no anonymous mode.

2. **Add the server to the user's MCP configuration**, keeping their existing entries:

   ```json
   {
     "mcpServers": {
       "kyrodata": {
         "url": "https://mcp.kyrodata.com/mcp",
         "headers": { "Authorization": "Bearer <THE_USER_KEY>" }
       }
     }
   }
   ```

   Some clients name the field `httpUrl` or need `"type": "http"`. Use whatever this
   client's own schema calls a remote streamable-HTTP server.

3. **Verify** by listing tools. You should get 12 or more, all prefixed `kyrodata_`. The
   cheapest check is `kyrodata_get_balance`, which costs no credits.

## Rules that matter

- **Never put the key in the URL.** Query strings land in browser history, proxy logs and
  shell history. The server only reads the `Authorization` header.
- **Do not invent an env var the client will not expand.** If the client cannot read
  `${KYRODATA_API_KEY}` from the environment, write the literal value into the config file
  the client owns, and tell the user where it landed.
- **Transport is `streamable-http`.** If the client offers a legacy "SSE" transport with a
  separate `/sse` endpoint, do not use it — that path is not served and will fail.
- **Do not set up a local process.** No `npx`, no Docker, no stdio wrapper. If the client
  only speaks stdio, `npx mcp-remote https://mcp.kyrodata.com/mcp --header "Authorization: Bearer <KEY>"`
  is the bridge — but prefer a native remote entry when one exists.

## What the user gets

Read-only tools over Brazilian foreign trade (MDIC/ComexStat), crop production, supply and
demand balances, climate readings and commodity forecasts. Every answer carries the window
it covers and the source it came from. Queries spend credits from the user's existing plan.
