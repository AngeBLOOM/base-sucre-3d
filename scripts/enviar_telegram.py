"""Manda imágenes a su chat de Telegram con el bot de la laptop (token en ~/.claude/channels/telegram/token.txt,
chat en access.json → allowFrom). Solo envía: no lee mensajes, así que no choca con el bot que está escuchando.

    python enviar_telegram.py "texto" archivo1.png archivo2.png ...

Las fotos van como documento (sin la compresión de Telegram) para que lleguen en 2K.
"""
import json
import mimetypes
import os
import sys
import urllib.request
import uuid

D = os.path.join(os.path.expanduser("~"), ".claude", "channels", "telegram")
TOKEN = open(os.path.join(D, "token.txt"), encoding="utf-8").read().strip()
CHAT = json.load(open(os.path.join(D, "access.json"), encoding="utf-8"))["allowFrom"][0]


def llamar(metodo, campos, archivo=None):
    limite = uuid.uuid4().hex
    cuerpo = b""
    for k, v in campos.items():
        cuerpo += f"--{limite}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
    if archivo:
        nombre = os.path.basename(archivo)
        tipo = mimetypes.guess_type(nombre)[0] or "application/octet-stream"
        cuerpo += (f"--{limite}\r\nContent-Disposition: form-data; name=\"document\"; filename=\"{nombre}\"\r\n"
                   f"Content-Type: {tipo}\r\n\r\n").encode() + open(archivo, "rb").read() + b"\r\n"
    cuerpo += f"--{limite}--\r\n".encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{TOKEN}/{metodo}", data=cuerpo,
                                 headers={"Content-Type": f"multipart/form-data; boundary={limite}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)["ok"]


texto, archivos = sys.argv[1], sys.argv[2:]
print("mensaje:", llamar("sendMessage", {"chat_id": CHAT, "text": texto}))
for a in archivos:
    print(os.path.basename(a), llamar("sendDocument", {"chat_id": CHAT}, a))
