# Fluxos de produção 100% na nuvem (Victor, 21/11/2026)

Regras gerais:
- **Telegram (grupo StudioTube) = armazém.** Todo bruto mora lá.
- **Drive (vichatori) = só mesa de edição:**
  - na hora de editar, o bruto desce do Telegram para o robô (e para o Drive, se precisar);
  - depois que o bruto foi 100% aproveitado, sai do Drive e fica só no Telegram;
  - o vídeo pronto fica no Drive até ser postado; depois vai para "✅ Vídeos postados" no Telegram e sai do Drive.
- **Limite de arquivo no Telegram: no máximo 1,5 GB por arquivo** (o Telegram aceita 2 GB; a folga evita erro). Toda live, podcast ou vídeo grande é dividido com `bash dividir.sh <video> <pasta>` antes de subir; na edição, `tg.js pegar` junta as partes.
- **Nada roda no PC** do Victor. Nada precisa de conversa aberta.
- **Aprovações vão para a Mesa do Escritório.**
- **Postagem:** Social Echo é a principal, e já foi testada no YouTube em 21/11. O Metricool é a reserva e traz os números.

Ferramentas: `tg.js` (`enviar` | `pegar` | `baixar` | `avisar`), robôs do GitHub (`.github/workflows`), rotinas do Claude na nuvem.

---

## Fluxo A · GTA VI (canal Direto de Vice)

| # | Etapa | Quem faz | Entra | Sai |
|---|---|---|---|---|
| A1 | Vigiar lives | robô `vigiar` (a cada 5 min) | `canais.json` (só canais com `autorizado: true`) | dispara o `gravar` |
| A2 | Gravar | robô `gravar` | live ao vivo | partes de 1 h no Telegram 📼 Lives brutas; a legenda começa com o NOME do arquivo; linha no `lives.md`. Se o Telegram falhar, a reserva vai para o Drive |
| A3 | Transcrever | robô `transcrever` (a cada hora) | `tg.js pegar lives NOME` | `transcricoes/NOME.json` (frases com tempo + picos de volume) |
| A4 | Escolher momentos | rotina do Claude "Produção GTA VI" | transcrição + temas outliers + `studiotube/gta-vi/` | 5–10 candidatos (cortes de 30 s–1 min 10 s; longos de 10–30 min) → **Mesa** (parada 1) |
| A5 | Montar o pedido | rotina do Claude | momentos aprovados na Mesa + Receita do campeão (`squad-outliers/ferramentas/receita.py montar --fluxo gta-vertical`) | `pedidos/AAAA-MM-DD-nome.json` com `"fonte": {"telegram": {"pasta":"lives","texto":"NOME"}}`, trechos, gancho, legendas em PT |
| A6 | Editar | robô `editar` (a cada 30 min) | pedido | vídeo 1080×1920 + conferência técnica → Drive `02-Prontos` + Telegram ✂️ Cortes |
| A7 | Conferir | rotina do Claude + fiscal de conteúdo | vídeo pronto + `receita.py conferir` | ficha do post (título, legenda, crédito ao creator, código GV-…) → **Mesa** (parada 2) |
| A8 | Postar | rotina do Claude (Social Echo) | aprovado na Mesa | post no YouTube Shorts, TikTok, Instagram e Pinterest; `publicado GV-… link` gravado sozinho |
| A9 | Guardar | robô | post feito | o vídeo vai para ✅ Vídeos postados no Telegram e sai do Drive; a live usada entra em `usadas.txt` |
| A10 | Aprender | rotina "Estudo dos campeões" (48 h e 7 dias) | números (Metricool / Social Echo) | `estudos/` e o caderno de aprendizados |

## Fluxo B · MESA DE MILIONÁRIO (Darks Clips, motivação)

| # | Etapa | Quem faz | Entra | Sai |
|---|---|---|---|---|
| B1 | Garimpar | rotinas "Outliers diários" e "Garimpo Darks" | criadores confirmados + 7 assuntos (`criterios-de-busca.md`) | listas no Telegram → Victor responde "ok 1 3 5" → base aprovada |
| B2 | Podcasts inteiros | robô `podcast` (a cada 2 h, 1 por vez) | `podcasts/fila.txt` | vídeo no Telegram 🧰 Material + `podcasts/transcricoes/ID.json` |
| B3 | Momentos dos podcasts | rotina do Claude "Podcasts: melhores momentos" | transcrição + 5 critérios de momento | lista de momentos → **Mesa** |
| B4 | Montar o pedido | rotina do Claude "Produção Darks Clips" | corte aprovado (base) ou momento do podcast + Receita (`--fluxo dark`) | `pedidos/...json` com `"fonte": {"youtube": link}` (baixa pelo @TopSaverBot) ou `{"url": tiktok}`; trechos de 15 s–1 min 10 s; gancho; palavras de impacto |
| B5 | Editar | robô `editar` | pedido | vídeo 1080×1920 → Drive + Telegram |
| B6 | Conferir | rotina do Claude + fiscal | vídeo + `receita.py conferir` | ficha (código DC-…) → **Mesa** |
| B7 | Postar | Social Echo | aprovado | contas da MESA DE MILIONÁRIO (a criar), com o Metricool de reserva |
| B8 | Guardar e aprender | igual a A9 e A10 | | |

## O que ainda falta para o fluxo ficar completo
1. **Editor da nuvem com a qualidade das skills.** Hoje o `editar.py` é simples: fundo desfocado, legenda e gancho. Falta trazer o padrão das skills `editar-dark` e `editar-gta`:
   - mapa da curva e SFX;
   - legenda Anton/Montserrat com ênfase dourada;
   - zoom nas reações;
   - clipes do banco (Darks).
2. **Rotina "Podcasts: melhores momentos"** (B3).
3. **Rotina de postagem** (A8/B7) com a Social Echo, que só posta o que estiver aprovado na Mesa.
4. **Contas da MESA DE MILIONÁRIO** (Victor).
5. **Juntar as rotinas** duplicadas num ambiente só.
