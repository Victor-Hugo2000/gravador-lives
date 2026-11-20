// Vigia os canais de canais.json (roda no GitHub a cada ~5 min).
// Para cada canal ao vivo com título de GTA que ainda não está sendo gravado, dispara o robô "gravar".
const fs = require("fs"), { spawnSync } = require("child_process");
const { canais, filtroTitulo } = JSON.parse(fs.readFileSync("canais.json", "utf8"));
const filtro = new RegExp(filtroTitulo, "i");
const MAX_SIMULTANEAS = 5;

const sh = (cmd, args) => spawnSync(cmd, args, { encoding: "utf8", timeout: 90000 }).stdout || "";

function aoVivo(url) {
  const out = sh("yt-dlp", ["--js-runtimes", "node", "--skip-download", "--no-warnings", "--print", "%(is_live)s\t%(title)s · %(description)s", url]);
  const linha = out.split("\n").find((l) => l.startsWith("True\t")) || "";
  if (!linha) return null;
  return linha.split("\t").slice(1).join(" ").replace(/\s+/g, " ").replace(/^.*?\(live\) \S+ \S+ \S /, "").replace(/ · NA$/, "").trim();
}

const ativos = JSON.parse(sh("gh", ["run", "list", "--workflow", "gravar.yml", "--limit", "60", "--json", "displayTitle,status"]) || "[]")
  .filter((r) => r.status !== "completed").map((r) => r.displayTitle.replace(/^gravar /, ""));
console.log("gravando agora:", ativos.join(", ") || "nenhum");

let total = ativos.length;
for (const c of canais) {
  if (ativos.includes(c.nome)) continue;
  if (total >= MAX_SIMULTANEAS) { console.log("limite de gravações simultâneas"); break; }
  for (const url of c.urls) {
    const titulo = aoVivo(url);
    if (!titulo) continue;
    if (!filtro.test(titulo)) { console.log(`${c.nome} ao vivo fora de GTA: ${titulo}`); break; }
    console.log(`GRAVAR ${c.nome}: ${titulo}`);
    sh("gh", ["workflow", "run", "gravar.yml", "-f", `canal=${c.nome}`, "-f", `url=${url}`, "-f", `titulo=${titulo.slice(0, 200)}`]);
    total++;
    break;
  }
}
