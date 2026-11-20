"""Transcreve uma live gravada para o Claude escolher os melhores momentos.
Uso: python transcrever.py <video> <saida.json>
Grava: idioma, duração, frases [inicio, fim, texto] e picos de volume (reação) por janela de 10 s."""
import json, subprocess, sys, array
from faster_whisper import WhisperModel

video, saida = sys.argv[1], sys.argv[2]
wav = video + ".wav"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", wav], check=True)
dados = array.array("h", open(wav, "rb").read())
janela = 16000 * 10
volume = []
for i in range(0, len(dados), janela):
    bloco = dados[i:i + janela]
    if bloco:
        volume.append(round((sum(x * x for x in bloco[::40]) / len(bloco[::40])) ** 0.5))
media = sorted(volume)[len(volume) // 2] or 1
picos = sorted(((v / media, i * 10) for i, v in enumerate(volume)), reverse=True)[:40]
modelo = WhisperModel("base", device="cpu", compute_type="int8")
import numpy as np
audio = (np.frombuffer(open(wav, "rb").read(), np.int16).astype(np.float32) / 32768.0)
segs, info = modelo.transcribe(audio, vad_filter=True, beam_size=1)
frases = [[round(s.start, 1), round(s.end, 1), s.text.strip()] for s in segs]
json.dump({"video": video, "idioma": info.language, "duracao": round(info.duration),
           "picosDeVolume": [{"segundo": s, "vezesAcimaDaMediana": round(x, 1)} for x, s in sorted(picos, key=lambda z: z[1])],
           "frases": frases}, open(saida, "w", encoding="utf8"), ensure_ascii=False)
print("ok", len(frases), "frases", info.language)
