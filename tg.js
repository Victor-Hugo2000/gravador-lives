// Arquivo do Direto de Vice no Telegram (grupo privado com pastas = tópicos).
// node tg.js login                      → no PC do Victor, uma vez: gera a autorização (fica em %APPDATA%\direto-de-vice\telegram.json)
// node tg.js criar                      → cria o grupo "Direto de Vice · Arquivo" com as pastas e grava tg.json
// node tg.js enviar <arquivo> <pasta> "<legenda>"   → pasta = lives | cortes | postados | material
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
  const r = await cli.invoke(new Api.channels.CreateChannel({ title: "Direto de Vice · Arquivo", about: "Arquivo do canal: lives brutas, cortes, vídeos postados e material.", megagroup: true, forum: true }));
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

const [cmd, ...a] = process.argv.slice(2);
({ login, criar, enviar: () => enviar(...a) })[cmd]?.().catch((e) => { console.error("ERRO:", e.message); process.exit(1); }) ?? console.log("uso: login | criar | enviar <arquivo> <pasta> <legenda>");
