#!/bin/bash
# Обёртка для запуска backup_db.py из cron.
# Даёт стабильное окружение: cd в корень проекта, exec python из venv.

set -e

cd /opt/legal_mind
exec /opt/legal_mind/venv/bin/python /opt/legal_mind/scripts/backup_db.py