<div align="center">

<img src="logo.png" alt="Kyrodata" width="88" height="88">

# Kyrodata

**Brazilian trade, crop and commodity data over MCP**

[![Quality, maintenance and endpoint health on Glama](https://glama.ai/mcp/servers/kyrodata/mcp/badges/score.svg)](https://glama.ai/mcp/servers/kyrodata/mcp)
[![catalog](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fkyrodata.com%2F.well-known%2Fmcp%2Fserver-card.json&query=%24.serverInfo.version&label=catalog&color=635BFF&style=flat-square)](https://kyrodata.com/en-US/developers?utm_source=github&utm_medium=readme&utm_campaign=mcp-directory)
[![tools](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fkyrodata.com%2F.well-known%2Fmcp%2Fserver-card.json&query=%24.tools.length&label=tools&color=635BFF&style=flat-square)](https://kyrodata.com/en-US/developers?utm_source=github&utm_medium=readme&utm_campaign=mcp-directory)
[![mcp registry](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fregistry.modelcontextprotocol.io%2Fv0.1%2Fservers%3Fsearch%3Dcom.kyrodata%26version%3Dlatest&query=%24.servers%5B0%5D.server.version&label=mcp%20registry&color=635BFF&style=flat-square)](https://registry.modelcontextprotocol.io/v0.1/servers?search=com.kyrodata&version=latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-635BFF?style=flat-square)](LICENSE)

</div>

Kyrodata is a **remote** [Model Context Protocol](https://modelcontextprotocol.io) server.
There is nothing to install or run: point your agent at the hosted endpoint and give it
your API key.

```
https://mcp.kyrodata.com/mcp
```

Ask in plain language — *"how did Brazil's coffee exports do this year against last?"* —
and get the measured figure, the window it covers, and the source behind it.

## Get a key

Create one at [kyrodata.com/user/api-keys](https://kyrodata.com/user/api-keys). It is shown
only once. Queries spend the credits already included in your plan — the connector is not a
separate subscription.

## Connect

**Any agent that accepts a header** (Cline, Claude Code, Cursor, VS Code, Codex, n8n,
Zapier, Make):

```json
{
  "mcpServers": {
    "kyrodata": {
      "url": "https://mcp.kyrodata.com/mcp",
      "headers": { "Authorization": "Bearer YOUR_KYRODATA_API_KEY" }
    }
  }
}
```

Command-line equivalents:

```bash
claude mcp add --transport http kyrodata https://mcp.kyrodata.com/mcp \
  --header "Authorization: Bearer $KYRODATA_API_KEY"

codex mcp add kyrodata --url https://mcp.kyrodata.com/mcp \
  --bearer-token-env-var KYRODATA_API_KEY

gemini mcp add --transport http --header "Authorization: Bearer $KYRODATA_API_KEY" \
  kyrodata https://mcp.kyrodata.com/mcp
```

**Chat assistants** (claude.ai, ChatGPT) have no field for a key — they ask for your
authorization instead. Add Kyrodata as a custom connector with the same URL and sign in when
prompted. Walkthrough per client: **[kyrodata.com/developers](https://kyrodata.com/en-US/developers?utm_source=github&utm_medium=readme&utm_campaign=mcp-directory)**.

## What you get

Read-only tools over Brazilian foreign trade (MDIC/ComexStat), crop production, supply and
demand balances, climate readings and commodity forecasts.

| Tool | What it answers |
| --- | --- |
| `kyrodata_search` | Search the public trade catalog |
| `kyrodata_fetch` | Open one public trade document by id |
| `kyrodata_resolve_entity` | Resolve country, HS code or commodity |
| `kyrodata_compare_trade` | Compare exports/imports between equal windows |
| `kyrodata_list_trade_series` | Raw monthly trade series as rows |
| `kyrodata_list_trade_partners` | Top partner countries with growth |
| `kyrodata_get_heading_overview` | Overview of an HS heading (SH4) |
| `kyrodata_resolve_comparison_window` | Build a like-for-like comparison window |
| `kyrodata_get_supply_demand_balance` | Supply and demand balance sheet |
| `kyrodata_get_climate_reading` | Climate reading and physical crop loss |
| `kyrodata_get_hub_summary` † | Commodity hub summary and forecast verdict |
| `kyrodata_explain_pyramid_level` † | Explain one level of the forecast pyramid |
| `kyrodata_run_report` | Run one of the catalog reports |
| `kyrodata_get_data_coverage` | Data coverage and latest closed month |
| `kyrodata_get_credit_balance` | Credit balance and limits for this key (free) |

`tools/list` on the live endpoint is the authoritative list.

† The two price-forecast tools are part of an additional plan. Trade, climate and
supply-and-demand tools are not.

## How it answers

- **Windows are equal-weight by construction.** Three months are never compared against a
  full year; the server refuses the unequal window and returns the largest matching one, labeled.
- **Every answer names its window and its source.**
- **"No signal" is a real answer** where the data does not support a verdict.
- **Read-only.** No tool writes, deletes or buys anything.

## Running it as a local command (you almost certainly should not)

`bridge/server.py` is a stdio-to-HTTP forwarder, and the `Dockerfile` packages
it. **This is not the server.** The server is remote, and any client that speaks
remote MCP should connect straight to the URL above — one hop fewer, nothing to
install. The bridge exists for two cases only: a client that can only launch a
local command, and a directory that will not score what it cannot build, start
and introspect.

```bash
docker build -t kyrodata-mcp .
docker run -i --rm -e KYRODATA_API_KEY=kd_live_... kyrodata-mcp
```

It implements no tools of its own: `initialize`, `tools/list` and `tools/call`
are forwarded verbatim, so there is no second copy of the catalogue here that
could drift from the server. Zero third-party dependencies, and the key never
goes into the image.

## Notes

- Transport is `streamable-http`. The deprecated HTTP+SSE transport is not served.
- Without credentials the endpoint answers `401` — never `403`.
- Keys go in the `Authorization` header. A key in a query string is not accepted, because
  query strings land in browser history and proxy logs.

MIT for this repository's contents. The hosted service has its own
[terms](https://kyrodata.com/en-US/terms).
