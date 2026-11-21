// Ponte entre as etapas do fluxo (skills do Claude) e a Mesa do Victor.
//
// Pedir aprovação (cria a tarefa na Mesa, ou leva a versão nova de uma devolvida):
//   node mesa.js pedir --projeto "c012 perseguição" --setor edicao --etapa mapa \
//     --titulo "Aprovar o mapa" --resumo "3 linhas do que mudou" --link "C:\...\mapa_v02.md"
//   --link é obrigatório: o Victor vê o material direto na tarefa (regra de 20/11).
//   Arquivo do Drive também serve: o Escritório descobre o tipo e busca na conta certa.
//
// Ler a decisão do Victor:
//   node mesa.js ler <id>
//
// Criar um vídeo novo com todas as tarefas do pipeline:
//   node mesa.js projeto "Faltam 3 dias - preço"
//
// Onde fica o escritório: ESCRITORIO_API e ESCRITORIO_TOKEN no backend/.env
// (na nuvem). Sem ESCRITORIO_API, usa o servidor do PC (localhost:3737).
// Com o escritório na nuvem, o link local vira:
//   - texto (.md/.txt/.json/.srt) → vai junto, guardado na tarefa;
//   - vídeo/áudio/imagem → sobe para o Drive do canal (pasta "Escritório - prévias").
//
// Sempre imprime JSON. Se o escritório estiver fora do ar, sai com código 2.

import { readFileSync, existsSync, statSync, createReadStream } from "node:fs";
import { Readable } from "node:stream";
import path from "node:path";
import { fileURLToPath } from "node:url";

const aqui = path.dirname(fileURLToPath(import.meta.url));

function lerEnv() {
  const arquivo = path.join(aqui, "..", ".env");
  const valores = {};
  if (existsSync(arquivo)) {
    for (const linha of readFileSync(arquivo, "utf-8").split(/\r?\n/)) {
      const m = linha.match(/^([A-Z0-9_]+)=(.*)$/);
      if (m) valores[m[1]] = m[2].trim().replace(/^["']|["']$/g, "");
    }
  }
  return { ...valores, ...process.env };
}

const env = lerEnv();
const API = (env.ESCRITORIO_API || "http://localhost:3737").replace(/\/$/, "");
// ESCRITORIO_NUVEM=1 força o jeito da nuvem (para testar no simulador local).
const NA_NUVEM = env.ESCRITORIO_NUVEM === "1" || !/localhost|127\.0\.0\.1/.test(API);

const EXT_TEXTO = /\.(md|txt|json|srt)$/i;
const MIDIA = [
  [/\.(mp4|mov|webm)$/i, "video", "video/mp4"],
  [/\.(mp3|wav|m4a)$/i, "audio", "audio/mpeg"],
  [/\.(png|jpe?g|webp)$/i, "imagem", "image/jpeg"],
  [/\.pdf$/i, "pdf", "application/pdf"],
];
const TIPOS = { ".mp4": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm", ".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".pdf": "application/pdf" };

function sair(codigo, dados) {
  console.log(JSON.stringify(dados));
  process.exit(codigo);
}

function lerOpcoes(args) {
  const opcoes = {};
  for (let i = 0; i < args.length; i++) {
    if (args[i].startsWith("--")) {
      opcoes[args[i].slice(2)] = args[i + 1];
      i++;
    }
  }
  return opcoes;
}

async function chamar(caminho, corpo) {
  const cabecalhos = {};
  if (env.ESCRITORIO_TOKEN) cabecalhos.Authorization = `Bearer ${env.ESCRITORIO_TOKEN}`;
  if (corpo) cabecalhos["Content-Type"] = "application/json";
  let resposta;
  try {
    resposta = await fetch(`${API}${caminho}`, corpo ? { method: "POST", headers: cabecalhos, body: JSON.stringify(corpo) } : { headers: cabecalhos });
  } catch {
    sair(2, {
      ok: false,
      erro: NA_NUVEM
        ? `Não consegui falar com o escritório na nuvem (${API}). Confira a internet e tente de novo em alguns minutos.`
        : "Escritório desligado. Rode `npm run dev` em C:\\DiretoDeVice\\escritorio-virtual.",
    });
  }
  const json = await resposta.json().catch(() => ({}));
  if (resposta.status === 401) sair(1, { ok: false, erro: "O escritório recusou a chave (ESCRITORIO_TOKEN no backend/.env)." });
  if (!resposta.ok) sair(1, { ok: false, ...json });
  return json;
}

// Conta 1 = Drive do Direto de Vice; conta 2 = Drive dos Darks (projetos "Darks · ...").
async function tokenGoogle(conta) {
  const r = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    body: new URLSearchParams({
      client_id: env.GOOGLE_CLIENT_ID,
      client_secret: env.GOOGLE_CLIENT_SECRET,
      refresh_token: conta === 2 ? env.GOOGLE_REFRESH_TOKEN_2 : env.GOOGLE_REFRESH_TOKEN,
      grant_type: "refresh_token",
    }),
  });
  const j = await r.json();
  if (!j.access_token) throw new Error(j.error_description || j.error || "sem acesso ao Google");
  return j.access_token;
}

async function pastaDasPrevias(token) {
  const nome = "Escritório - prévias";
  const q = encodeURIComponent(`name = '${nome}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false`);
  const busca = await (await fetch(`https://www.googleapis.com/drive/v3/files?q=${q}&fields=files(id)`, { headers: { Authorization: `Bearer ${token}` } })).json();
  if (busca.files?.[0]?.id) return busca.files[0].id;
  const criada = await (await fetch("https://www.googleapis.com/drive/v3/files?fields=id", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ name: nome, mimeType: "application/vnd.google-apps.folder" }),
  })).json();
  return criada.id;
}

// Sobe a prévia para o Drive do canal e devolve o link.
async function subirPrevia(caminho, conta) {
  const tamanho = statSync(caminho).size;
  if (tamanho > 1024 * 1024 * 1024) throw new Error("arquivo maior que 1 GB: mande uma prévia leve");
  const token = await tokenGoogle(conta);
  const pasta = await pastaDasPrevias(token);
  const tipo = TIPOS[path.extname(caminho).toLowerCase()] || "application/octet-stream";
  const inicio = await fetch("https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable&fields=id", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json; charset=UTF-8",
      "X-Upload-Content-Type": tipo,
      "X-Upload-Content-Length": String(tamanho),
    },
    body: JSON.stringify({ name: path.basename(caminho), parents: [pasta] }),
  });
  const destino = inicio.headers.get("location");
  if (!destino) throw new Error(`o Drive recusou o envio (${inicio.status})`);
  const envio = await fetch(destino, {
    method: "PUT",
    headers: { "Content-Length": String(tamanho), "Content-Type": tipo },
    body: Readable.toWeb(createReadStream(caminho)),
    duplex: "half",
  });
  const feito = await envio.json();
  if (!feito.id) throw new Error("o Drive não devolveu o arquivo");
  return `https://drive.google.com/file/d/${feito.id}/view`;
}

const [comando, ...resto] = process.argv.slice(2);

if (comando === "pedir") {
  const o = lerOpcoes(resto);
  const corpo = { projeto: o.projeto, setor: o.setor, etapa: o.etapa, titulo: o.titulo, resumo: o.resumo, link: o.link, midia: o.midia };
  // Regra do Victor (20/11): todo material que ele aprova fica no Escritório, para ver direto na tarefa.
  if (!o.link) sair(1, { ok: false, erro: "Toda aprovação leva o material: passe --link com o arquivo (vídeo, imagem, áudio, PDF ou texto .md/.txt)." });
  const local = o.link && !/^https?:\/\//i.test(o.link);
  if (local && NA_NUVEM) {
    if (!existsSync(o.link)) sair(1, { ok: false, erro: `Arquivo não encontrado: ${o.link}` });
    if (EXT_TEXTO.test(o.link)) {
      corpo.conteudo = readFileSync(o.link, "utf-8").replace(/^﻿/, "");
      corpo.midia = "texto";
      delete corpo.link; // texto vai dentro da tarefa; caminho do PC a nuvem recusa
    } else {
      const tipo = MIDIA.find(([re]) => re.test(o.link));
      if (!tipo) sair(1, { ok: false, erro: "Tipo de arquivo sem prévia (use .mp4, .mp3, .wav, .png, .jpg, .pdf, .md ou .txt)." });
      try {
        const conta = /^darks/i.test(o.projeto || "") && env.GOOGLE_REFRESH_TOKEN_2 ? 2 : 1;
        corpo.link = await subirPrevia(o.link, conta);
        corpo.midia = tipo[1];
      } catch (e) {
        sair(1, { ok: false, erro: `Não consegui subir a prévia para o Drive: ${e.message}` });
      }
    }
  }
  const t = await chamar("/api/mesa/pedir", corpo);
  console.log(JSON.stringify({ ok: true, id: t.id, status: t.status, versao: t.versao, link: corpo.link ?? null }));
} else if (comando === "ler") {
  const t = await chamar(`/api/tarefas/${resto[0]}`);
  // situacao: "esperando" (Victor ainda não decidiu), "aprovado" ou "devolvido".
  // retorno: o pedido (devolvido) ou a observação (aprovado).
  const situacao = t.decisao === "aprovado" ? "aprovado" : t.decisao === "devolvido" ? "devolvido" : "esperando";
  console.log(JSON.stringify({ ok: true, id: t.id, situacao, versao: t.versao, retorno: t.retorno, decididoEm: t.decidido_em }));
} else if (comando === "pensando") {
  // node mesa.js pensando <setor> "o que estou fazendo"   |   node mesa.js pensando <setor> off
  const [setor, ...texto] = resto;
  const desligar = texto.length === 0 || texto.join(" ") === "off";
  await chamar(`/api/setores/${setor}/pensando`, { ativo: !desligar, mensagem: desligar ? "" : texto.join(" ") });
  console.log(JSON.stringify({ ok: true, setor, ativo: !desligar }));
} else if (comando === "projeto") {
  const r = await chamar("/api/projetos", { nome: resto.join(" ") });
  console.log(JSON.stringify({ ok: true, id: r.projeto.id, criado: r.criado }));
} else {
  sair(1, { ok: false, erro: "Uso: node mesa.js pedir --projeto .. --setor .. --etapa .. --titulo .. [--resumo ..] [--link ..] [--midia ..] | ler <id> | projeto <nome> | pensando <setor> \"texto\"|off" });
}
