# sparkhub_tiktok_chat.py
# FASE 5: LEITOR DE MENTES TIKTOK (GHOST READER)
# TIPAGEM FORTE | NULOS SEGUROS | ASYNC DRIVEN

from TikTokLive import TikTokLiveClient
from TikTokLive.events import ConnectEvent, CommentEvent, GiftEvent, DisconnectEvent
import asyncio
import sqlite3
import datetime
import traceback

from sparkhub_paths import get_path

class TikTokGhostReader:
    def __init__(self, username: str, db_path: str | None = None):
        self.username = username
        self.db_path = db_path if db_path else str(get_path("mempalace.db"))
        self.client = TikTokLiveClient(unique_id=self.username)
        self._register_events()

    def _register_events(self):
        @self.client.on(ConnectEvent)
        async def on_connect(event: ConnectEvent):
            print(f"[TIKTOK-GHOST] Conectado na Room ID: {event.room_id}")

        @self.client.on(DisconnectEvent)
        async def on_disconnect(event: DisconnectEvent):
            print("[TIKTOK-GHOST] Desconectado. O Circuit Breaker interno do TikTokLive tentará reconectar...")

        @self.client.on(CommentEvent)
        async def on_comment(event: CommentEvent):
            msg = f"{event.user.nickname}: {event.comment}"
            print(f"[CHAT] {msg}")
            self._save_memory("Chat", msg)

        @self.client.on(GiftEvent)
        async def on_gift(event: GiftEvent):
            # Agrupa os presentes para evitar flood no DB
            if event.gift.streakable and not event.gift.streaking:
                msg = f"{event.user.nickname} enviou {event.gift.count}x {event.gift.info.name}"
                print(f"[GIFT] 🎁 {msg}")
                self._save_memory("Gift", msg)
            elif not event.gift.streakable:
                msg = f"{event.user.nickname} enviou {event.gift.info.name}"
                print(f"[GIFT] 🎁 {msg}")
                self._save_memory("Gift", msg)

    def _save_memory(self, event_type: str, content: str):
        try:
            with sqlite3.connect(self.db_path, timeout=10) as conn:
                conn.execute(
                    "INSERT INTO memories (wing, content, updated_at) VALUES (?, ?, ?)",
                    (f"TikTok_{event_type}", content, datetime.datetime.now(datetime.UTC).isoformat())
                )
        except Exception as e:
            print(f"[MURPHY-ALRT] Falha ao salvar memória no SQLite: {e}")

    def start(self):
        print(f"[ANTIFRAGILIDADE] Iniciando Leitor Fantasma para @{self.username}...")
        try:
            self.client.run()
        except Exception as e:
            print(f"[MURPHY-ALRT] Falha crítica na thread do TikTok: {e}")
            print(traceback.format_exc())

if __name__ == "__main__":
    # Teste de conexão (substitua pelo arroba real da sua conta na hora da live)
    ghost = TikTokGhostReader(username="jubileu_steampunk_test")
    
    # IMPORTANTE: Descomente a linha abaixo para iniciar a leitura.
    # ghost.start()
    print("[TIKTOK-GHOST] Estrutura do Leitor Fantasma compilada com sucesso!")
