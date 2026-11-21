"""Banco de cenas da MESA DE MILIONÁRIO (Drive vichatori).
  python3 edicao/cenas.py indexar    → acrescenta ao fim de cenas/indice.json as cenas novas do Drive
  python3 edicao/cenas.py organizar  → move/renomeia no Drive as cenas já catalogadas para
                                        'Darks Clips/Banco de Cenas/<pasta>/<nome>-<NNNN>.mp4'
O número NNNN (posição no índice) nunca muda: liga índice, miniatura e catálogo."""
import json, os, re, subprocess, sys, unicodedata

BANCO = "Darks Clips/Banco de Cenas"
ORIGENS = ["Dinheiro & Money 2.0", "Lifestyle Variado 2.0", "Filmes 2.0", BANCO]
PASTAS = ["Dinheiro e Luxo", "Carros", "Estrada e Viagem", "Natureza e Paisagem", "Céu e Espaço", "Cidade e Noite",
          "Silhueta e Solidão", "Treino e Disciplina", "Trabalho e Estudo", "Pessoas e Lifestyle", "Animais",
          "Água e Mar", "Fogo e Tempestade", "Cinema e Drama", "Outros", "Não serve"]
VIDEO = (".mp4", ".mov", ".webm", ".mkv")

def carregar(f, padrao):
    return json.load(open(f, encoding="utf8")) if os.path.exists(f) else padrao

def salvar(f, d):
    json.dump(d, open(f, "w", encoding="utf8"), ensure_ascii=False, indent=1)

def slug(t):
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:50] or "cena"

def indexar():
    idx = carregar("cenas/indice.json", {"cenas": []})
    conhecidos = {c["drive"] for c in idx["cenas"]}
    novos = 0
    for p in ORIGENS:
        r = subprocess.run(["rclone", "lsjson", "-R", "--files-only", "drive:" + p], capture_output=True, text=True)
        for f in json.loads(r.stdout or "[]"):
            caminho = p + "/" + f["Path"]
            if f["Name"].lower().endswith(VIDEO) and caminho not in conhecidos:
                idx["cenas"].append({"drive": caminho, "pasta": p, "nome": f["Name"], "mb": round(f["Size"] / 1e6, 1)})
                conhecidos.add(caminho); novos += 1
    idx["total"] = len(idx["cenas"])
    salvar("cenas/indice.json", idx)
    print("cenas novas:", novos, "| total:", idx["total"])

def organizar(limite=400):
    idx = carregar("cenas/indice.json", {"cenas": []})
    cat = carregar("cenas/catalogo.json", {})
    movidas = 0
    for n, c in enumerate(idx["cenas"]):
        k = f"{n:04d}"; e = cat.get(k)
        ja_na_pasta = any(c["drive"].startswith(f"{BANCO}/{p}/") for p in PASTAS)
        if not e or ja_na_pasta or c.get("organizada"):
            continue
        pasta = e.get("pasta") if e.get("pasta") in PASTAS else ("Não serve" if e.get("serve") is False else "Outros")
        ext = os.path.splitext(c["drive"])[1].lower() or ".mp4"
        novo = f"{BANCO}/{pasta}/{slug(e.get('nome') or e.get('descricao', 'cena'))}-{k}{ext}"
        if subprocess.run(["rclone", "moveto", "drive:" + c["drive"], "drive:" + novo]).returncode == 0:
            c["origem"] = c["drive"]; c["drive"] = novo; c["pasta"] = pasta; c["nome"] = os.path.basename(novo); c["organizada"] = True
            e["drive"] = novo; e["pasta"] = pasta
            movidas += 1
            if movidas >= limite: break
    salvar("cenas/indice.json", idx); salvar("cenas/catalogo.json", cat)
    print("cenas organizadas agora:", movidas)

if __name__ == "__main__":
    {"indexar": indexar, "organizar": organizar}[sys.argv[1]]()
