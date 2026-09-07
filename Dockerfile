# O que esta imagem containeriza e a PONTE stdio (bridge/server.py), nao o
# Kyrodata. O servidor MCP real e remoto: https://mcp.kyrodata.com/mcp, e todo
# cliente que fala HTTP remoto deve ligar direto nele -- um salto a menos e nada
# a instalar. Esta imagem existe para dois casos, e so para eles:
#   1. cliente que so sabe subir um comando local (stdio);
#   2. diretorio que so pontua o que ele mesmo consegue construir, subir e
#      inspecionar -- o check do Glama e desse tipo.
#
# A ponte nao implementa ferramenta nenhuma: encaminha `initialize`,
# `tools/list` e `tools/call` tal e qual. Por isso nao existe um segundo
# catalogo aqui dentro que possa divergir do servidor.
#
# Zero dependencia de terceiro (so biblioteca padrao), entao nao ha
# requirements.txt nem camada de pip.
# PRECISA de saida para a internet: sem alcancar mcp.kyrodata.com a ponte nao
# responde nem ao `initialize`.
FROM python:3.12-slim

WORKDIR /app
COPY bridge/server.py ./server.py

# Sem root: este processo so precisa de stdio e uma conexao HTTPS de saida.
RUN useradd --create-home --uid 10001 bridge
USER bridge

# Buffer trava JSON-RPC sobre stdio: o cliente espera a linha de resposta e ela
# fica presa no buffer.
ENV PYTHONUNBUFFERED=1

# A chave NUNCA entra na imagem -- passe em tempo de execucao:
#   docker run -i --rm -e KYRODATA_API_KEY=kd_live_... <imagem>
ENTRYPOINT ["python3", "server.py"]
