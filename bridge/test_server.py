#!/usr/bin/env python3
"""O que a ponte promete, afirmado contra um servidor de mentira.

A ponte nao implementa ferramenta nenhuma -- ela ENCAMINHA. Entao o que da para
quebrar aqui nao e resposta de tool: e o transporte. Cada teste abaixo prende um
comportamento que o `server.py` descreve em prosa e que ninguem mais verifica.

Zero dependencia de terceiro e zero rede de verdade: um `http.server` local faz
de servidor remoto, e a ponte roda como subprocesso, falando stdio, como um
cliente falaria com ela. Rodar: `python3 -m unittest discover -s bridge`.
"""
import json
import os
import subprocess
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BRIDGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.py")


class _Handler(BaseHTTPRequestHandler):
    """Servidor de mentira: guarda o que recebeu e devolve o que mandaram devolver."""

    def do_POST(self):  # noqa: N802 -- nome exigido por BaseHTTPRequestHandler
        body = self.rfile.read(int(self.headers.get("content-length", 0)))
        # urllib capitaliza o nome do cabecalho ("Authorization"); HTTP nao
        # diferencia maiuscula, e o teste nao deve fingir que diferencia.
        headers = {k.lower(): v for k, v in self.headers.items()}
        self.server.received.append({"headers": headers, "body": json.loads(body)})
        status, ctype, payload, extra = self.server.script.pop(0)
        self.send_response(status)
        self.send_header("content-type", ctype)
        for k, v in extra.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(payload.encode("utf-8"))

    def log_message(self, *_args):
        pass  # silencio: o unittest ja e o relatorio


class BridgeCase(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self.server.received = []
        self.server.script = []
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.shutdown)
        self.url = "http://127.0.0.1:%d/mcp" % self.server.server_address[1]

    def run_bridge(self, lines, api_key="kd_live_test", timeout=20):
        env = dict(os.environ, KYRODATA_MCP_URL=self.url, KYRODATA_TIMEOUT="10")
        if api_key is None:
            env.pop("KYRODATA_API_KEY", None)
        else:
            env["KYRODATA_API_KEY"] = api_key
        out = subprocess.run(
            [sys.executable, BRIDGE],
            input="".join(l + "\n" for l in lines),
            capture_output=True, text=True, env=env, timeout=timeout,
        ).stdout
        return [json.loads(l) for l in out.splitlines() if l.strip()]

    def reply(self, payload, status=200, ctype="application/json", **extra):
        self.server.script.append((status, ctype, json.dumps(payload), extra))

    # -- o encaminhamento e literal: o que o servidor responde e o que sai ------
    def test_forwards_the_response_unchanged(self):
        self.reply({"jsonrpc": "2.0", "id": 1, "result": {"tools": [{"name": "kyrodata_search"}]}})
        got = self.run_bridge(['{"jsonrpc":"2.0","id":1,"method":"tools/list"}'])
        self.assertEqual(got, [{"jsonrpc": "2.0", "id": 1, "result": {"tools": [{"name": "kyrodata_search"}]}}])
        self.assertEqual(self.server.received[0]["body"]["method"], "tools/list")

    # -- a chave vira `Authorization: Bearer`, que e o que o servidor exige -----
    def test_sends_bearer_when_the_key_is_set(self):
        self.reply({"jsonrpc": "2.0", "id": 1, "result": {}})
        self.run_bridge(['{"jsonrpc":"2.0","id":1,"method":"initialize"}'], api_key="kd_live_abc")
        self.assertEqual(self.server.received[0]["headers"]["authorization"], "Bearer kd_live_abc")

    def test_omits_the_header_without_a_key(self):
        self.reply({"jsonrpc": "2.0", "id": 1, "result": {}})
        self.run_bridge(['{"jsonrpc":"2.0","id":1,"method":"initialize"}'], api_key=None)
        self.assertNotIn("authorization", self.server.received[0]["headers"])

    # -- a sessao do Streamable HTTP: sai no initialize, volta na proxima -------
    def test_keeps_the_session_across_calls(self):
        self.reply({"jsonrpc": "2.0", "id": 1, "result": {}}, **{"mcp-session-id": "sess-42"})
        self.reply({"jsonrpc": "2.0", "id": 2, "result": {}})
        self.run_bridge([
            '{"jsonrpc":"2.0","id":1,"method":"initialize"}',
            '{"jsonrpc":"2.0","id":2,"method":"tools/list"}',
        ])
        self.assertNotIn("mcp-session-id", self.server.received[0]["headers"])
        self.assertEqual(self.server.received[1]["headers"]["mcp-session-id"], "sess-42")

    # -- SSE: a ULTIMA linha `data:` e a resposta; as anteriores sao progresso --
    def test_reads_the_last_data_line_of_an_sse_body(self):
        self.server.script.append((
            200, "text/event-stream",
            'data: {"jsonrpc":"2.0","id":1,"result":{"step":1}}\n\n'
            'data: {"jsonrpc":"2.0","id":1,"result":{"final":true}}\n\n',
            {},
        ))
        got = self.run_bridge(['{"jsonrpc":"2.0","id":1,"method":"tools/call"}'])
        self.assertEqual(got, [{"jsonrpc": "2.0", "id": 1, "result": {"final": True}}])

    # -- 401 com corpo JSON-RPC e resposta legitima: passa como veio ------------
    def test_passes_a_json_rpc_error_body_through(self):
        self.reply(
            {"jsonrpc": "2.0", "id": 1, "error": {"code": -32000, "message": "Chave malformada."}},
            status=401,
        )
        got = self.run_bridge(['{"jsonrpc":"2.0","id":1,"method":"initialize"}'])
        self.assertEqual(got[0]["error"]["message"], "Chave malformada.")

    # -- notificacao nao tem resposta; escrever uma dessincroniza o cliente -----
    def test_writes_nothing_for_a_notification(self):
        self.reply({"jsonrpc": "2.0", "id": None, "result": {}})
        self.reply({"jsonrpc": "2.0", "id": 7, "result": {}})
        got = self.run_bridge([
            '{"jsonrpc":"2.0","method":"notifications/initialized"}',
            '{"jsonrpc":"2.0","id":7,"method":"tools/list"}',
        ])
        self.assertEqual([m["id"] for m in got], [7])

    # -- linha que nao e JSON vira -32700, e a ponte segue viva ----------------
    def test_answers_parse_error_and_keeps_going(self):
        self.reply({"jsonrpc": "2.0", "id": 2, "result": {}})
        got = self.run_bridge(['nao sou json', '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'])
        self.assertEqual(got[0]["error"]["code"], -32700)
        self.assertEqual(got[1]["id"], 2)


if __name__ == "__main__":
    unittest.main()
