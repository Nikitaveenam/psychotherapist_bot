import os
import subprocess
import datetime
import requests
import shutil
from pathlib import Path
from dotenv import load_dotenv

# --- Загрузка .env ---
load_dotenv()

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# --- Директория для бэкапов ---
backup_dir = Path("backups")
backup_dir.mkdir(exist_ok=True)

# --- Имя файла бэкапа ---
today = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
filename = f"backup_{today}.dump"
backup_path = backup_dir / filename

# --- Поиск pg_dump ---
pg_dump_path = shutil.which("pg_dump")
if not pg_dump_path:
    possible_dirs = [
        "C:\\Program Files\\PostgreSQL",
        "C:\\Program Files (x86)\\PostgreSQL"
    ]
    for base in possible_dirs:
        if os.path.exists(base):
            for version in os.listdir(base):
                candidate = os.path.join(base, version, "bin", "pg_dump.exe")
                if os.path.isfile(candidate):
                    pg_dump_path = candidate
                    break
if not pg_dump_path:
    print("❌ Не удалось найти pg_dump.exe. Убедитесь, что PostgreSQL установлен.")
    exit(1)

# --- Бэкап ---
os.environ["PGPASSWORD"] = DB_PASSWORD
dump_command = [
    pg_dump_path,
    "-U", DB_USER,
    "-h", DB_HOST,
    "-p", DB_PORT,
    "-F", "c",
    "-f", str(backup_path),
    DB_NAME
]

result = subprocess.run(dump_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

if result.returncode == 0:
    print(f"✅ Бэкап создан: {backup_path}")

    try:
        with open(backup_path, "rb") as f:
            response = requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument",
                data={"chat_id": CHAT_ID},
                files={"document": f}
            )
        if response.status_code == 200:
            print("📦 Отправлено в Telegram")

            # --- Удаление старых бэкапов ---
            DAYS_TO_KEEP = 3
            now = datetime.datetime.now()
            for file in backup_dir.glob("backup_*.dump"):
                mtime = datetime.datetime.fromtimestamp(file.stat().st_mtime)
                if (now - mtime).days > DAYS_TO_KEEP:
                    try:
                        file.unlink()
                        print(f"🗑 Удалён: {file.name}")
                    except Exception as e:
                        print(f"⚠️ Ошибка удаления {file.name}: {e}")
        else:
            print(f"❌ Ошибка отправки в Telegram: {response.text}")
    except Exception as e:
        print(f"❌ Ошибка отправки в Telegram: {e}")
else:
    print("❌ Ошибка создания бэкапа:")
    print(result.stderr.decode())
