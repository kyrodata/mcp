#!/usr/bin/env python3
"""stdio -> Streamable HTTP bridge for the Kyrodata MCP server.

O servidor REAL e remoto: https://mcp.kyrodata.com/mcp. Cliente que fala HTTP
remoto deve ligar direto nele -- um salto a menos e nada a instalar. Esta ponte
existe para dois casos, e so para eles:

  1. cliente que so sabe subir um comando local (stdio);
  2. diretorio que exige "constroi, sobe, responde a introspeccao" para pontuar
     (o check de release do Glama e desse tipo).

A ponte NAO implementa ferramenta nenhuma: `initialize`, `tools/list` e
`tools/call` sao encaminhados tal e qual. Por isso nao existe uma segunda
definicao de catalogo nesta imagem que possa divergir do servidor -- que e o
defeito que este arquivo existe para nao ter.

Zero dependencia de terceiro (so biblioteca padrao), entao nao ha requirements
nem camada de pip. PRECISA de saida para a internet: sem alcancar
mcp.kyrodata.com a ponte nao responde nem ao `initialize`.

A chave NUNCA vai na imagem -- passe em tempo de execucao com
`-e KYRODATA_API_KEY=kd_live_...`. Sem ela o servidor responde 401 a tudo,
inclusive ao `initialize`, e a ponte repassa esse erro como veio.
"""
import json
import os
import sys
import urllib.error
import urllib.request

ENDPOINT = os.environ.get("KYRODATA_MCP_URL", "https://mcp.kyrodata.com/mcp")
API_KEY = os.environ.get("KYRODATA_API_KEY", "")
TIMEOUT = float(os.environ.get("KYRODATA_TIMEOUT", "60"))

# O servidor devolve JSON ou SSE conforme o Accept; pedimos os dois e tratamos
# os dois, que e o que a especificacao de Streamable HTTP manda o cliente fazer.
BASE_HEADERS = {
    "content-type": "application/json",
    "accept": "application/json, text/event-stream",
    "user-agent": "kyrodata-stdio-bridge/1.0",
}

# Streamable HTTP entrega a sessao no cabecalho da resposta do initialize e a
# exige de volta nas chamadas seguintes. Guardar isto e o unico estado da ponte.
session_id = None


def _headers():
    h = dict(BASE_HEADERS)
    if API_KEY:
        h["authorization"] = "Bearer " + API_KEY
    if session_id:
        h["mcp-session-id"] = session_id
    return h


def _parse(body, content_type):
    """SSE ou JSON puro -> o objeto JSON-RPC. Em SSE, a ultima linha `data:`
    e a resposta; as anteriores sao progresso, que stdio nao transporta."""
    text = body.decode("utf-8", "replace").strip()
    if not text:
        return None
    if "text/event-stream" in (content_type or ""):
        payload = None
        for line in text.splitlines():
            if line.startswith("data:"):
                payload = line[5:].strip()
        text = payload or ""
        if not text:
            return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def forward(message):
    global session_id
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(message).encode("utf-8"),
        headers=_headers(),
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
            sid = res.headers.get("mcp-session-id")
            if sid:
                session_id = sid
            return _parse(res.read(), res.headers.get("content-type"))
    except urllib.error.HTTPError as err:
        # 401 e resposta legitima do servidor (falta chave, chave revogada) e o
        # corpo ja e JSON-RPC: repassar como veio diz a verdade ao cliente.
        parsed = _parse(err.read(), err.headers.get("content-type"))
        if parsed is not None:
            return parsed
        return {
            "jsonrpc": "2.0",
            "id": message.get("id"),
            "error": {"code": -32603, "message": "HTTP %d from %s" % (err.code, ENDPOINT)},
        }
    except Exception as err:  # rede fora, DNS, timeout
        return {
            "jsonrpc": "2.0",
            "id": message.get("id"),
            "error": {"code": -32603, "message": "%s: %s" % (type(err).__name__, err)},
        }


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            sys.stdout.write(json.dumps({
                "jsonrpc": "2.0", "id": None,
                "error": {"code": -32700, "message": "Parse error"},
            }) + "\n")
            sys.stdout.flush()
            continue

        response = forward(message)

        # Notificacao (sem `id`) nao tem resposta. Escrever uma quebra o cliente,
        # que estaria esperando a resposta da PROXIMA requisicao.
        if message.get("id") is None:
            continue
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
