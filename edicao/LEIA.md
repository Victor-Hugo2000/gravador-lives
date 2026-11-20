# Edição na nuvem (GTA VI e Darks Clips)

Os robôs do GitHub editam; o Claude escolhe o que editar.

1. **`transcrever.yml`** (de hora em hora): pega as lives novas de canais **autorizados** em `canais.json`, transcreve e grava `transcricoes/<live>.json` (frases com tempo e picos de volume).
2. **Tarefas do Claude** ("Produção GTA VI" e "Produção Darks Clips"): leem as transcrições ou a base aprovada, escolhem os trechos, escrevem gancho e legendas e criam um pedido em `pedidos/AAAA-MM-DD-nome.json`.
3. **`editar.yml`** (quando chega pedido, e a cada 30 min): renderiza com `edicao/editar.py` (vertical 1080x1920, fundo desfocado, legenda grande de até 3 palavras, gancho no topo, volume padronizado), salva no Drive em `Direto de Vice/<GTA VI|Darks Clips>/02-Prontos/`, manda para a pasta "✂️ Cortes" do Telegram e move o pedido para `pedidos/feitos/`.

## Pedido (exemplo)
```json
{
  "projeto": "darks-clips",
  "fonte": {"url": "https://www.tiktok.com/@perfil/video/123"},
  "trechos": [{"inicio": 0, "fim": 42.5}],
  "gancho": "NINGUÉM CRESCE NO CONFORTO",
  "legendas": "auto",
  "idioma": "pt",
  "titulo": "Ninguém cresce no conforto #disciplina",
  "saida": "2026-11-21-ninguem-cresce-no-conforto.mp4",
  "baseId": "tt:123"
}
```
GTA VI: `"fonte": {"drive": "Direto de Vice/01-Brutos/Lives/<arquivo>.mp4"}` e `"legendas"` com a tradução em português escrita pelo Claude, com tempos relativos ao vídeo montado (`[{"inicio","fim","texto"}]`), ou `"auto"`.

Vídeo pronto **não é vídeo postado**: postar continua com o ok do Victor.
