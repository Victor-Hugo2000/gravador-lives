"""Renderiza um pedido de edição da StudioTube (GTA VI ou Darks Clips).
Uso: python editar.py <pedido.json> <pasta_de_trabalho>
O pedido diz a fonte (arquivo do Drive ou link), os trechos, o gancho e as legendas.
Saída: <pasta>/<saida>.mp4 vertical 1080x1920 com legenda queimada e gancho no topo."""
import json, os, subprocess, sys

def sh(*a):
    print("+", " ".join(map(str, a))[:300], flush=True)
    subprocess.run(list(map(str, a)), check=True)

def tempo_ass(s):
    h, r = divmod(max(s, 0), 3600); m, s = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"

def limpar(t):
    return t.replace("{", "(").replace("}", ")").replace("\n", " ").strip()

def audio_de(video):
    """Lê o áudio com o ffmpeg (16 kHz mono) para a transcrição, sem depender da biblioteca 'av'."""
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)

def blocos_auto(video, idioma):
    """Transcreve o vídeo montado e devolve legendas de até 3 palavras."""
    from faster_whisper import WhisperModel
    modelo = WhisperModel(os.environ.get("WHISPER", "small"), device="cpu", compute_type="int8")
    segs, _ = modelo.transcribe(audio_de(video), language=idioma or None, word_timestamps=True, vad_filter=True)
    palavras = [w for s in segs for w in (s.words or [])]
    out, grupo = [], []
    for w in palavras:
        grupo.append(w)
        fim_frase = w.word.strip()[-1:] in ".!?,"
        if len(grupo) == 3 or fim_frase:
            out.append({"inicio": grupo[0].start, "fim": grupo[-1].end, "texto": "".join(x.word for x in grupo)})
            grupo = []
    if grupo:
        out.append({"inicio": grupo[0].start, "fim": grupo[-1].end, "texto": "".join(x.word for x in grupo)})
    return out

# Acabamento por operação (21/11/2026):
#  GTA VI  → Montserrat ExtraBold branca com contorno, palavra com "salto"; gancho em tarja amarela.
#  MESA DE MILIONÁRIO → Anton caixa alta, palavras de impacto em DOURADO (#D4AF37) maiores; gancho Anton branco.
ESTILOS = {
    "gta-vi": ("Style: Legenda,Montserrat ExtraBold,92,&H00FFFFFF,&H00FFFFFF,&H00000000,&H78000000,-1,0,0,0,100,100,0,0,1,8,3,2,70,70,560,1\n"
               "Style: Gancho,Montserrat ExtraBold,66,&H00000000,&H00000000,&H0000E5FF,&H0000E5FF,-1,0,0,0,100,100,0,0,3,20,0,8,70,70,200,1\n"),
    # Padrão MESA DE MILIONÁRIO (referência caverna-flavio_v03 e missao-cadar_v02, Victor 21/11):
    # legenda pequena Anton branca, 1 a 3 palavras, sem caixa; a palavra de impacto ganha linha própria e um de 4 estilos;
    # gancho no topo em 2 linhas (pequena branca + Anton dourada); "gigante" = palavra enorme dourada no topo.
    "darks-clips": ("Style: Legenda,Anton,74,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,0,0,0,0,100,100,1,0,1,2.5,2,2,80,80,560,1\n"
                    "Style: Gancho,Montserrat SemiBold,40,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,0,0,0,0,100,100,2,0,1,1.5,1,8,80,80,150,1\n"
                    "Style: Gancho2,Anton,86,&H0037AFD4,&H0037AFD4,&H00000000,&H64000000,0,0,0,0,100,100,1,0,1,2,2,8,80,80,200,1\n"
                    "Style: Gigante,Anton,250,&H0037AFD4,&H0037AFD4,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,0,3,8,20,20,150,1\n"),
}
DOURADO = "&H0037AFD4&"
# tipos de ênfase (pedido "enfase": ["PALAVRA"] ou [{"palavra": "FOME", "tipo": "vermelho"}])
ENFASE = {
    "ouro-serifa": "{\\fnDM Serif Display\\i1\\c&H0037AFD4&\\fs112\\bord2}",
    "vermelho": "{\\c&H2B2BE8&\\fs128}",
    "script": "{\\fnGreat Vibes\\c&H0037AFD4&\\fs150\\bord1}",
    "ouro": "{\\c&H0037AFD4&\\fs118}",
}

def escrever_ass(caminho, legendas, gancho, duracao, projeto="gta-vi", enfase=()):
    cab = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 0\n\n[V4+ Styles]\n"
           "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
           + ESTILOS.get(projeto, ESTILOS["gta-vi"]) +
           "\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    imp = {}
    for x in enfase:
        if isinstance(x, dict):
            imp[limpar(x["palavra"]).upper().strip(".,!?")] = x.get("tipo", "ouro-serifa")
        else:
            imp[limpar(x).upper().strip(".,!?")] = "ouro-serifa"
    linhas = []
    if gancho:
        g = limpar(gancho).upper()
        if projeto == "darks-clips":
            # "CERTEZA OU TALVEZ?" ou "ESCOLHEU? | VAI ATÉ O FIM." (2ª parte em Anton dourada)
            p1, _, p2 = g.partition("|")
            fim_g = tempo_ass(min(duracao, 3.5))
            linhas.append(f"Dialogue: 2,{tempo_ass(0)},{fim_g},Gancho,,0,0,0,,{{\\fad(0,250)}}{p1.strip()}")
            if p2.strip():
                linhas.append(f"Dialogue: 2,{tempo_ass(0)},{fim_g},Gancho2,,0,0,0,,{{\\fad(0,250)}}{p2.strip()}")
        else:
            efeito = "{\\fscx70\\fscy70\\t(0,120,\\fscx104\\fscy104)\\t(120,200,\\fscx100\\fscy100)}"
            linhas.append(f"Dialogue: 1,{tempo_ass(0)},{tempo_ass(duracao)},Gancho,,0,0,0,,{efeito}{g}")
    for l in legendas:
        txt = limpar(l["texto"]).upper()
        if not txt:
            continue
        if projeto == "darks-clips":
            partes, atual = [], []
            for w in txt.split():
                tipo = imp.get(w.strip(".,!?"))
                if tipo == "gigante":
                    linhas.append(f"Dialogue: 0,{tempo_ass(l['inicio'])},{tempo_ass(l['fim'] + 0.05)},Gigante,,0,0,0,,"
                                  f"{{\\fad(80,80)\\fscx94\\fscy94\\t(0,400,\\fscx100\\fscy100)}}{w.strip('.,!?')}")
                    atual.append(w)
                elif tipo:
                    if atual: partes.append(" ".join(atual)); atual = []
                    partes.append(ENFASE.get(tipo, ENFASE["ouro-serifa"]) + (w.title() if tipo == "script" else w) + "{\\r}")
                else:
                    atual.append(w)
            if atual: partes.append(" ".join(atual))
            corpo = "{\\fad(90,60)}" + "\\N".join(partes)
        else:
            corpo = "{\\fscx78\\fscy78\\t(0,90,\\fscx110\\fscy110)\\t(90,170,\\fscx100\\fscy100)}" + txt
        linhas.append(f"Dialogue: 0,{tempo_ass(l['inicio'])},{tempo_ass(l['fim'] + 0.05)},Legenda,,0,0,0,,{corpo}")
    open(caminho, "w", encoding="utf8").write(cab + "\n".join(linhas) + "\n")

def duracao_de(v):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", v], capture_output=True, text=True)
    return float(r.stdout.strip() or 0)

def conferir(video):
    """Conferência técnica: tamanho, duração, som e tela preta. Devolve a lista de problemas (vazia = ok)."""
    problemas = []
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                        "-of", "csv=p=0", video], capture_output=True, text=True).stdout.strip()
    if r != "1080,1920":
        problemas.append(f"tamanho {r}, esperado 1080x1920")
    d = duracao_de(video)
    if not 15 <= d <= 70:
        problemas.append(f"duração {d:.0f} s, fora de 15 s a 1 min 10 s")
    a = subprocess.run(["ffmpeg", "-v", "info", "-i", video, "-af", "volumedetect", "-vn", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    import re
    m = re.search(r"mean_volume: (-?[\d.]+) dB", a)
    if not m:
        problemas.append("sem som")
    elif float(m.group(1)) < -35:
        problemas.append(f"som muito baixo ({m.group(1)} dB)")
    b = subprocess.run(["ffmpeg", "-v", "info", "-i", video, "-vf", "blackdetect=d=1.5:pix_th=0.1", "-an", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    for x in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", b):
        problemas.append(f"tela preta de {float(x[0]):.0f} a {float(x[1]):.0f} s")
    return problemas

def main(pedido_json, pasta):
    p = json.load(open(pedido_json, encoding="utf8"))
    os.makedirs(pasta, exist_ok=True)
    src = os.path.join(pasta, "fonte.mp4")
    f = p["fonte"]
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if "telegram" in f:
        # bruto no grupo StudioTube: {"telegram": {"pasta": "lives", "texto": "<nome da live>"}}; junta as partes
        t = f["telegram"]; dp = os.path.join(pasta, "partes")
        sh("node", os.path.join(raiz, "tg.js"), "pegar", t.get("pasta", "lives"), t["texto"], dp)
        partes = sorted(x for x in os.listdir(dp) if x.endswith(".mp4"))
        with open(os.path.join(pasta, "lista.txt"), "w") as L:
            for x in partes: L.write(f"file '{os.path.join(os.path.abspath(dp), x)}'\n")
        sh("ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", os.path.join(pasta, "lista.txt"), "-c", "copy", src)
    elif "drive" in f:
        sh("rclone", "copyto", "drive:" + f["drive"], src)
    elif "youtube" in f or "youtube.com" in f.get("url", "") or "youtu.be" in f.get("url", ""):
        # YouTube bloqueia robôs: baixa pelo @TopSaverBot no Telegram
        sh("node", os.path.join(raiz, "tg.js"), "baixar", "@TopSaverBot", f.get("youtube") or f["url"], src, "30")
    else:
        sh("yt-dlp", "--no-warnings", "-f", "bv*[height<=1080]+ba/b", "--merge-output-format", "mp4", "-o", src, f["url"])
    vertical = ("[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:2,setsar=1[bg];"
                "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,setsar=1[fg];"
                "[bg][fg]overlay=(W-w)/2:(H-h)/2,fps=30,format=yuv420p[v]")
    partes = []
    trechos = p.get("trechos") or [{"inicio": 0, "fim": duracao_de(src)}]
    for i, t in enumerate(trechos):
        parte = os.path.join(pasta, f"parte{i:02d}.mp4")
        sh("ffmpeg", "-v", "error", "-y", "-ss", t["inicio"], "-i", src, "-t", float(t["fim"]) - float(t["inicio"]),
           "-filter_complex", vertical, "-map", "[v]", "-map", "0:a:0?", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "160k", parte)
        partes.append(parte)
    lista = os.path.join(pasta, "lista.txt")
    open(lista, "w").write("".join(f"file '{os.path.abspath(x)}'\n" for x in partes))
    base = os.path.join(pasta, "base.mp4")
    sh("ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lista, "-c", "copy", base)
    # MESA DE MILIONÁRIO: mantém o ÁUDIO da referência e troca a imagem por cenas do banco em trechos marcados.
    # "cenas": [{"em": 3.2, "dur": 2.5, "drive": "Dinheiro & Money 2.0/carro.mp4", "de": 0}]  (tempos no vídeo montado)
    cenas = p.get("cenas") or []
    mesa = p.get("projeto") == "darks-clips"
    if cenas or mesa:
        # Padrão MESA (vídeo de referência 'caverna-flavio_v03', 20/11): quem fala em PRETO E BRANCO escurecido com vinheta;
        # cenas do banco coloridas, escurecidas, com vinheta, entrando com fusão curta.
        grade_fala = "hue=s=0,eq=contrast=1.12:brightness=-0.05,vignette=PI/4.5" if mesa else "null"
        grade_cena = "eq=brightness=-0.06:saturation=0.9:contrast=1.05,vignette=PI/4.5" if mesa else "null"
        entradas, filtros, ult = ["-i", base], [f"[0:v]{grade_fala}[g0]"], "[g0]"
        for i, c in enumerate(cenas, start=1):
            arq = os.path.join(pasta, f"cena{i:02d}.mp4")
            sh("rclone", "copyto", "drive:" + c["drive"], arq)
            entradas += ["-ss", c.get("de", 0), "-t", c["dur"], "-i", arq]
            em, fim = float(c["em"]), float(c["em"]) + float(c["dur"])
            filtros.append(f"[{i}:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30,{grade_cena},"
                           f"format=yuva420p,fade=in:st=0:d=0.18:alpha=1,setpts=PTS-STARTPTS+{em}/TB[c{i}]")
            filtros.append(f"{ult}[c{i}]overlay=0:0:eof_action=pass:enable='between(t,{em},{fim})'[v{i}]")
            ult = f"[v{i}]"
        mesclado = os.path.join(pasta, "mesclado.mp4")
        sh("ffmpeg", "-v", "error", "-y", *entradas, "-filter_complex", ";".join(filtros), "-map", ult, "-map", "0:a:0?",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "copy", mesclado)
        base = mesclado
    dur = duracao_de(base)
    leg = p.get("legendas", "auto")
    if leg == "auto":
        leg = blocos_auto(base, p.get("idioma", "pt"))
    ass = os.path.join(pasta, "legenda.ass")
    escrever_ass(ass, leg or [], p.get("gancho", ""), dur, p.get("projeto", "gta-vi"), p.get("enfase", []))
    final = os.path.join(pasta, p["saida"])
    sh("ffmpeg", "-v", "error", "-y", "-i", base, "-vf", f"ass={ass}:fontsdir={os.environ.get('FONTES', 'fontes')}", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
       "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", final)
    problemas = conferir(final)
    json.dump({"video": p["saida"], "duracao": round(duracao_de(final), 1), "problemas": problemas},
              open(os.path.join(pasta, "conferencia.json"), "w", encoding="utf8"), ensure_ascii=False)
    print("PRONTO", final, f"{dur:.1f}s", "| conferência:", "; ".join(problemas) or "ok", flush=True)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
