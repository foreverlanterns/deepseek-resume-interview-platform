#!/bin/sh
set -eu

echo "[entrypoint] 等待数据库可用..."
python - <<'PY'
import os
import sys
import time

import psycopg

url = os.environ["DATABASE_URL"]
for prefix in ("postgresql+asyncpg://", "postgresql+psycopg://"):
    if url.startswith(prefix):
        url = "postgresql://" + url[len(prefix) :]
        break

last_error: Exception | None = None
for attempt in range(1, 31):
    try:
        with psycopg.connect(url, connect_timeout=3) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            print("[entrypoint] 数据库已就绪")
            break
    except Exception as exc:  # noqa: BLE001 - 启动阶段需要打印所有连接错误
        last_error = exc
        print(f"[entrypoint] 数据库未就绪（{attempt}/30）：{exc}")
        time.sleep(2)
else:
    print("[entrypoint] 数据库连接超时，拒绝启动", file=sys.stderr)
    raise SystemExit(1) from last_error
PY

echo "[entrypoint] 执行数据库迁移..."
alembic upgrade head

echo "[entrypoint] 启动应用：$*"
exec "$@"
