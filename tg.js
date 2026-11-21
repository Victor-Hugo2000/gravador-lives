// Arquivo da StudioTube no Telegram (grupo privado com pastas = tópicos).
// node tg.js login                      → no PC do Victor, uma vez: gera a autorização (fica em %APPDATA%\direto-de-vice\telegram.json)
// node tg.js criar                      → cria o grupo "StudioTube" com as pastas e grava tg.json
// node tg.js enviar <arquivo> <pasta> "<legenda>"   → pasta = lives | cortes | postados | material
// node tg.js avisar <pasta> "<texto>"               → mensagem de texto numa pasta (avisos da Agenda e da Produção)
// node tg.js achar <texto> | baixar <@bot> <link> <saida>  → download pelo bot do Telegram (Top Saver Bot)
// node tg.js pegar <pasta> "<texto>" <saida>      → baixa do grupo as partes de uma live/vídeo (edição na nuvem lê daqui)
// Na nuvem a autorização vem do segredo TG_CONF (o mesmo JSON), nunca de arquivo do repositório.
const fs = require("fs"), path = require("path"), os = require("os");
const { TelegramClient, Api } = require("telegram");
const { StringSession } = require("telegram/sessions");
const PASTAS = { lives: "📼 Lives brutas", cortes: "✂️ Cortes aprovados", postados: "✅ Vídeos postados", material: "🧰 Material (sons, imagens, referências)" };
const LOCAL = path.join(process.env.APPDATA || os.homedir(), "direto-de-vice", "telegram.json");
const TGJSON = path.join(__dirname, "tg.json");

function conf() {
  if (process.env.TG_CONF) return JSON.parse(process.env.TG_CONF);
  if (fs.existsSync(LOCAL)) return JSON.parse(fs.readFileSync(LOCAL, "utf8"));
  throw new Error("sem autorização do Telegram: rode 'node tg.js login'");
}
async function cliente(c) {
  const cli = new TelegramClient(new StringSession(c.session || ""), Number(c.api_id), c.api_hash, { connectionRetries: 5 });
  cli.setLogLevel("error");
  return cli;
}
const pergunta = (q) => new Promise((r) => { const rl = require("readline").createInterface({ input: process.stdin, output: process.stdout }); rl.question(q, (a) => { rl.close(); r(a.trim()); }); });

async function login() {
  console.log("Pegue o api_id e o api_hash em https://my.telegram.org → API development tools.");
  const api_id = await pergunta("api_id: "), api_hash = await pergunta("api_hash: ");
  const cli = await cliente({ api_id, api_hash });
  await cli.start({
    phoneNumber: () => pergunta("Seu número com DDI (ex.: +5511999999999): "),
    phoneCode: () => pergunta("Código que chegou no Telegram: "),
    password: () => pergunta("Senha de verificação em duas etapas (se tiver; senão Enter): "),
    onError: (e) => console.log("erro:", e.message),
  });
  fs.mkdirSync(path.dirname(LOCAL), { recursive: true });
  fs.writeFileSync(LOCAL, JSON.stringify({ api_id, api_hash, session: cli.session.save() }));
  console.log("\nPronto! Autorização guardada em " + LOCAL);
  await cli.disconnect(); process.exit(0);
}

async function criar() {
  const cli = await cliente(conf()); await cli.connect();
  const r = await cli.invoke(new Api.channels.CreateChannel({ title: "StudioTube", about: "Arquivo da StudioTube: lives brutas, cortes, vídeos postados e material de todos os canais.", megagroup: true, forum: true }));
  const canal = r.chats[0];
  const out = { channelId: canal.id.toString(), accessHash: canal.accessHash.toString(), pastas: {} };
  const peer = new Api.InputChannel({ channelId: canal.id, accessHash: canal.accessHash });
  for (const [k, titulo] of Object.entries(PASTAS)) {
    const t = await cli.invoke(new Api.channels.CreateForumTopic({ channel: peer, title: titulo, randomId: BigInt(Date.now()) * 1000n + BigInt(Math.floor(Math.random() * 1000)) }));
    const u = t.updates.find((x) => x.message && x.message.id);
    out.pastas[k] = u.message.id;
  }
  fs.writeFileSync(TGJSON, JSON.stringify(out, null, 2));
  console.log("grupo criado:", JSON.stringify(out));
  await cli.disconnect(); process.exit(0);
}

async function enviar(arquivo, pasta, legenda) {
  const g = JSON.parse(fs.readFileSync(TGJSON, "utf8"));
  if (!g.pastas[pasta]) throw new Error("pasta desconhecida: " + pasta);
  const cli = await cliente(conf()); await cli.connect();
  const peer = new Api.InputPeerChannel({ channelId: BigInt(g.channelId), accessHash: BigInt(g.accessHash) });
  let ult = 0;
  await cli.sendFile(peer, {
    file: arquivo, caption: legenda.slice(0, 1000), replyTo: g.pastas[pasta], supportsStreaming: true, workers: 4, forceDocument: false,
    progressCallback: (p) => { const pc = Math.floor(p * 100); if (pc >= ult + 10) { ult = pc; console.log(`enviando ${path.basename(arquivo)}: ${pc}%`); } },
  });
  console.log("ENVIADO", path.basename(arquivo), "→", PASTAS[pasta]);
  await cli.disconnect(); process.exit(0);
}

async function avisar(pasta, texto) {
  const g = JSON.parse(fs.readFileSync(TGJSON, "utf8"));
  if (!g.pastas[pasta]) throw new Error("pasta desconhecida: " + pasta);
  const cli = await cliente(conf()); await cli.connect();
  const peer = new Api.InputPeerChannel({ channelId: BigInt(g.channelId), accessHash: BigInt(g.accessHash) });
  for (let i = 0; i < texto.length; i += 3900) await cli.sendMessage(peer, { message: texto.slice(i, i + 3900), replyTo: g.pastas[pasta], linkPreview: false });
  console.log("AVISO ENVIADO →", PASTAS[pasta]);
  await cli.disconnect(); process.exit(0);
}


// node tg.js achar <texto>                 → lista conversas/bots com esse nome (ex.: achar saver)
async function achar(txt) {
  const cli = await cliente(conf()); await cli.connect();
  for await (const d of cli.iterDialogs({ limit: 300 })) {
    const e = d.entity || {}; const nome = (d.title || d.name || '') + ' @' + (e.username || '');
    if (nome.toLowerCase().includes(String(txt).toLowerCase())) console.log((e.bot ? 'BOT ' : '') + nome);
  }
  await cli.disconnect(); process.exit(0);
}
// node tg.js baixar <@bot> <link> <arquivo-saida> [minutos=20]
// manda o link ao bot de download, aperta o botão de melhor qualidade (até 1080p) se ele perguntar, e salva o 1º vídeo que voltar.
async function baixar(bot, link, saida, min = 20) {
  const cli = await cliente(conf()); await cli.connect();
  const ent = await cli.getEntity(bot);
  const enviada = await cli.sendMessage(ent, { message: link });
  const fim = Date.now() + Number(min) * 60000; const vistos = new Set(); let clicou = 0;
  while (Date.now() < fim) {
    await new Promise((r) => setTimeout(r, 5000));
    const msgs = await cli.getMessages(ent, { limit: 15, minId: enviada.id });
    for (const m of [...msgs].reverse()) {
      if (m.out || vistos.has(m.id + ':' + (m.editDate || 0))) continue;
      vistos.add(m.id + ':' + (m.editDate || 0));
      if (m.message) console.log('BOT:', m.message.slice(0, 300).replace(/\n/g, ' | '));
      const doc = m.media && (m.video || m.document);
      if (doc) {
        console.log('baixando arquivo do bot...');
        await cli.downloadMedia(m, { outputFile: saida, progressCallback: (a, t) => process.stdout.write(' ' + Math.round(Number(a) * 100 / Number(t || 1)) + '%') });
        console.log('\nSALVO', saida); await cli.disconnect(); process.exit(0);
      }
      if (m.buttons && clicou < 3) {
        const todos = m.buttons.flat(); const pref = ['1080', '720', 'mp4', 'vídeo', 'video', 'download', 'baixar'];
        let b = null; for (const p of pref) { b = todos.find((x) => (x.text || '').toLowerCase().includes(p)); if (b) break; }
        if (b) { console.log('apertando:', b.text); await m.click({ text: b.text }); clicou++; }
        else console.log('BOTÕES:', todos.map((x) => x.text).join(' / '));
      }
    }
  }
  console.error('ERRO: o bot não devolveu vídeo em ' + min + ' min'); await cli.disconnect(); process.exit(2);
}

// node tg.js pegar <pasta> "<texto da legenda>" <pasta-saida>
// baixa do grupo StudioTube todos os vídeos daquela pasta cuja legenda tem o texto (ex.: o nome da live), em ordem: parte01.mp4, parte02.mp4...
async function pegar(pasta, texto, dir) {
  const g = JSON.parse(fs.readFileSync(TGJSON, "utf8"));
  if (!g.pastas[pasta]) throw new Error("pasta desconhecida: " + pasta);
  const cli = await cliente(conf()); await cli.connect();
  const peer = new Api.InputPeerChannel({ channelId: BigInt(g.channelId), accessHash: BigInt(g.accessHash) });
  const achadas = [];
  for await (const m of cli.iterMessages(peer, { replyTo: g.pastas[pasta], limit: 3000 })) if (m.media && (m.video || m.document) && (m.message || "").includes(texto)) achadas.push(m);
  if (!achadas.length) { console.error("ERRO: nada no Telegram com: " + texto); await cli.disconnect(); process.exit(2); }
  achadas.sort((a, b) => a.id - b.id);
  fs.mkdirSync(dir, { recursive: true });
  let i = 0;
  for (const m of achadas) {
    i++; const out = path.join(dir, `parte${String(i).padStart(2, "0")}.mp4`);
    console.log(`baixando ${i}/${achadas.length} (msg ${m.id})`);
    await cli.downloadMedia(m, { outputFile: out, workers: 4 });
  }
  console.log("PEGUEI", achadas.length, "parte(s) em", dir);
  await cli.disconnect(); process.exit(0);
}

const [cmd, ...a] = process.argv.slice(2);
({ login, criar, enviar: () => enviar(...a), avisar: () => avisar(...a), achar: () => achar(...a), baixar: () => baixar(...a), pegar: () => pegar(...a) })[cmd]?.().catch((e) => { console.error("ERRO:", e.message); process.exit(1); }) ?? console.log("uso: login | criar | enviar | avisar | achar | baixar");
