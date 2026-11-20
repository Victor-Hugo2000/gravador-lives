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

def escrever_ass(caminho, legendas, gancho, duracao):
    cab = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Legenda,DejaVu Sans,86,&H00FFFFFF,&H0000FFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,7,3,2,70,70,520,1
Style: Gancho,DejaVu Sans,68,&H0000F0FF,&H0000F0FF,&H00000000,&HA0000000,-1,0,0,0,100,100,0,0,3,18,0,8,60,60,190,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    linhas = []
    if gancho:
        linhas.append(f"Dialogue: 1,{tempo_ass(0)},{tempo_ass(duracao)},Gancho,,0,0,0,,{limpar(gancho).upper()}")
    for l in legendas:
        txt = limpar(l["texto"]).upper()
        if txt:
            linhas.append(f"Dialogue: 0,{tempo_ass(l['inicio'])},{tempo_ass(l['fim'] + 0.05)},Legenda,,0,0,0,,{{\\fad(40,0)}}{txt}")
    open(caminho, "w", encoding="utf8").write(cab + "\n".join(linhas) + "\n")

def duracao_de(v):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", v], capture_output=True, text=True)
    return float(r.stdout.strip() or 0)

def main(pedido_json, pasta):
    p = json.load(open(pedido_json, encoding="utf8"))
    os.makedirs(pasta, exist_ok=True)
    src = os.path.join(pasta, "fonte.mp4")
    f = p["fonte"]
    if "drive" in f:
        sh("rclone", "copyto", "drive:" + f["drive"], src)
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
    dur = duracao_de(base)
    leg = p.get("legendas", "auto")
    if leg == "auto":
        leg = blocos_auto(base, p.get("idioma", "pt"))
    ass = os.path.join(pasta, "legenda.ass")
    escrever_ass(ass, leg or [], p.get("gancho", ""), dur)
    final = os.path.join(pasta, p["saida"])
    sh("ffmpeg", "-v", "error", "-y", "-i", base, "-vf", f"ass={ass}", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
       "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", final)
    print("PRONTO", final, f"{dur:.1f}s", flush=True)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
