"""Posta um vídeo pronto no YouTube (Shorts) pela API oficial.
Uso: python publicar_youtube.py <pedido_de_postagem.json> <video.mp4>
Credenciais só pelos segredos do GitHub: YT_CLIENT_ID, YT_CLIENT_SECRET e o token do canal
(YT_REFRESH_TOKEN_GTA para o GTA VI, YT_REFRESH_TOKEN_DARKS para o Darks Clips)."""
import json, os, sys, urllib.parse, urllib.request

p = json.load(open(sys.argv[1], encoding="utf8")); video = sys.argv[2]
token_canal = {"gta-vi": "YT_REFRESH_TOKEN_GTA", "darks-clips": "YT_REFRESH_TOKEN_DARKS"}[p["projeto"]]
cid, csec, rtok = os.environ.get("YT_CLIENT_ID"), os.environ.get("YT_CLIENT_SECRET"), os.environ.get(token_canal)
if not (cid and csec and rtok):
    print("DESLIGADO: faltam as credenciais do YouTube para", p["projeto"]); sys.exit(3)

def post(url, dados, cab):
    req = urllib.request.Request(url, data=dados, headers=cab, method="POST")
    with urllib.request.urlopen(req) as r: return r.headers, r.read()

_, corpo = post("https://oauth2.googleapis.com/token", urllib.parse.urlencode(
    {"client_id": cid, "client_secret": csec, "refresh_token": rtok, "grant_type": "refresh_token"}).encode(),
    {"Content-Type": "application/x-www-form-urlencoded"})
acesso = json.loads(corpo)["access_token"]
meta = {
    "snippet": {"title": p["titulo"][:100], "description": p.get("descricao", ""), "tags": p.get("tags", []),
                "categoryId": p.get("categoria", "20" if p["projeto"] == "gta-vi" else "22"), "defaultLanguage": "pt-BR"},
    "status": {"privacyStatus": p.get("privacidade", "private"), "selfDeclaredMadeForKids": False,
               "containsSyntheticMedia": bool(p.get("feitoComIA", False))},
}
if p.get("quando"):  # agendado: o YouTube publica sozinho nesse horário (ISO, ex. 2026-11-22T18:00:00-03:00)
    meta["status"].update({"privacyStatus": "private", "publishAt": p["quando"]})
cab, _ = post("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
              json.dumps(meta).encode(), {"Authorization": f"Bearer {acesso}", "Content-Type": "application/json",
                                          "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(os.path.getsize(video))})
_, corpo = post(cab["Location"], open(video, "rb").read(), {"Authorization": f"Bearer {acesso}", "Content-Type": "video/mp4"})
vid = json.loads(corpo)["id"]
print("POSTADO", f"https://www.youtube.com/shorts/{vid}")
open(os.environ.get("GITHUB_OUTPUT", "/dev/null"), "a").write(f"link=https://www.youtube.com/shorts/{vid}\n")
