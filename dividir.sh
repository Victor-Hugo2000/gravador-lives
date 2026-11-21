#!/bin/bash
# REGRA (Victor, 21/11/2026): todo arquivo que vai ao Telegram tem no MÁXIMO 1,5 GB (limite do Telegram é 2 GB; folga contra erro).
# Uso: bash dividir.sh <video.mp4> <pasta-saida>   → pasta-saida/<nome>_p01.mp4, _p02...  (sem reencodar)
set -e
ARQ="$1"; OUT="$2"; MAX=1500000000; ALVO=1300000000; FF=${FFMPEG:-ffmpeg}; FP=${FFPROBE:-ffprobe}
mkdir -p "$OUT"; BASE=$(basename "${ARQ%.mp4}")
TAM=$(stat -c %s "$ARQ")
if [ "$TAM" -le "$ALVO" ]; then cp "$ARQ" "$OUT/${BASE}_p01.mp4"; exit 0; fi
DUR=$($FP -v error -show_entries format=duration -of csv=p=0 "$ARQ" | cut -d. -f1)
SEG=$(( DUR * ALVO / TAM )); [ "$SEG" -lt 60 ] && SEG=60
$FF -v error -i "$ARQ" -c copy -map 0 -f segment -segment_time $SEG -reset_timestamps 1 -segment_start_number 1 "$OUT/${BASE}_p%02d.mp4"
for P in "$OUT"/*.mp4; do
  if [ "$(stat -c %s "$P")" -gt "$MAX" ]; then echo "ERRO: parte acima de 1,5 GB: $P"; exit 3; fi
done
ls "$OUT" | wc -l | xargs echo "partes:"
