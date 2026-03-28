# YCLIENTS Parser

В проекте есть два режима работы:

1. CLI через [handler.py](/Users/rvsmulskiy/code/YC-parser/handler.py)
2. Веб-интерфейс через [app.py](/Users/rvsmulskiy/code/YC-parser/app.py)

## CLI

```bash
/Users/rvsmulskiy/code/YC-parser/.venv/bin/python /Users/rvsmulskiy/code/YC-parser/handler.py \
  'https://n625088.yclients.com/company/266762/personal/select-master?o='
```

## Web UI

Установка зависимостей:

```bash
/Users/rvsmulskiy/code/YC-parser/.venv/bin/pip install -r /Users/rvsmulskiy/code/YC-parser/requirements.txt
```

Запуск сервера:

```bash
/Users/rvsmulskiy/code/YC-parser/.venv/bin/python /Users/rvsmulskiy/code/YC-parser/app.py
```

После запуска:

```text
Пользовательский интерфейс: http://localhost:8000/
Админка: http://localhost:8000/admin
```

## Docker

Локальная сборка:

```bash
docker build -t yc-parser-web /Users/rvsmulskiy/code/YC-parser
```

Локальный запуск:

```bash
docker run --rm -p 8000:8000 yc-parser-web
```
