# ChVB Stats -- Статистика Чемпионатов Великобритании по ЧГК

Парсер и визуализатор данных с [rating.chgk.info](https://rating.chgk.info) для всех Чемпионатов Великобритании по интеллектуальным играм (2008--2026).

**Результат**: [imangulova.github.io/chvb-stats](https://imangulova.github.io/chvb-stats/)

## Как это работает

### 1. API rating.chgk.info

Сайт рейтинга ЧГК предоставляет REST API. Авторизация не нужна для чтения.

**Базовый URL**: `https://api.rating.chgk.net`

**Заголовок**: обязательно `Accept: application/json`, иначе отдаёт HTML или LD+JSON.

**Ключевые эндпоинты**:

```
GET /                                    # Список всех эндпоинтов (accept: application/ld+json)
GET /countries                           # Все страны
GET /towns?country={id}                  # Города по стране
GET /players?surname={фамилия}           # Поиск игроков
GET /players/{id}                        # Профиль игрока
GET /players/{id}/tournaments            # Все турниры игрока
GET /teams?name={название}               # Поиск команд
GET /teams/{id}                          # Профиль команды
GET /tournaments?town={id}&page={n}      # Турниры по городу (30 на страницу)
GET /tournaments?name={название}         # Поиск по названию
GET /tournaments/{id}                    # Детали турнира
GET /tournaments/{id}/results            # Результаты турнира
GET /tournaments/{id}/results?includeTeamMembers=1&includeTeamFlags=1  # С составами и флагами
GET /seasons                             # Список сезонов
GET /releases                            # Релизы рейтинга
```

**Пагинация**: по 30 элементов на страницу, `?page=1`, `?page=2`, и т.д. Если вернулось < 30 -- последняя страница.

**Фильтры**: `?town=178` (по городу), `?name=Чемпионат` (по имени), `?properties.maiiRating=true` (только МАИИ). Важно: параметр именно `town=`, а не `idtown=`.

### 2. Структура данных

**Страны и города (UK)**:
- Великобритания: country_id = 8
- Лондон: 178, Кембридж: 1686, Бат: 1736, Манчестер: 1737, Глазго: 1760, Эдинбург: 1767, Оксфорд: 1770, Халифакс: 1806, Абердин: 1917, Ноттингем: 1924, Лидс: 2281

**Типы турниров**: "Обычный" (очный), "Синхрон", "Асинхрон"

**Флаги результатов** (появились с ~2019):
- `id=50, shortName="ЧСт"` -- "Зачёт чемпионата страны" (команда играет в зачёт ЧВБ)
- `id=1, shortName="!"` -- "Общий зачёт" (вне зачёта чемпионата, гостевая команда)

В старых турнирах (до 2019) флагов нет -- определяем зачёт по принадлежности города команды к UK.

### 3. Скрипт-парсер

`fetch_data.py` -- скачивает данные с API и сохраняет в `data/`:

```python
#!/usr/bin/env python3
"""Fetch ChVB tournament data from rating.chgk.info API."""

import urllib.request
import json
import time
from pathlib import Path

API = "https://api.rating.chgk.net"
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# All ChVB tournament IDs (found via tournaments?name=Великобритан + manual)
CHVB_IDS = [
    333, 444, 619, 1821, 2091, 2347, 2823, 3214, 3797,
    4255, 4856, 5448, 6114, 7805, 9038, 10237, 11919, 13612,
]


def api_get(path):
    url = f"{API}{path}"
    req = urllib.request.Request(url, headers={"accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def fetch_all():
    data = {}
    for tid in CHVB_IDS:
        print(f"Fetching tournament {tid}...", flush=True)
        info = api_get(f"/tournaments/{tid}")
        results = api_get(f"/tournaments/{tid}/results?includeTeamMembers=1&includeTeamFlags=1")
        data[str(tid)] = {"info": info, "results": results}
        print(f"  {info['name']} ({info['dateStart'][:10]}) -- {len(results)} teams")
        time.sleep(0.3)

    out = DATA_DIR / "chvb_results.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved to {out} ({out.stat().st_size:,} bytes)")


if __name__ == "__main__":
    fetch_all()
```

### 4. Генератор HTML

`build_stats.py` -- читает `data/chvb_results.json` и генерирует `chvb_stats.html` / `index.html`:

- Определяет зачёт ЧВБ: флаг ЧСт > ручные оверрайды > фоллбэк на UK-города
- Считает победы, подиумы, участия по игрокам и командам
- Генерирует self-contained HTML с dark/light темой, фильтрами по годам, ссылками на rating.chgk.info

### 5. Деплой на GitHub Pages

```bash
# Скачать данные
python3 fetch_data.py

# Сгенерировать HTML
python3 build_stats.py

# Скопировать как index.html для Pages
cp chvb_stats.html index.html

# Запушить
git add -A && git commit -m "Update stats" && git push
```

GitHub Pages автоматически раздаёт `index.html` по адресу `https://{username}.github.io/{repo}/`.

## Как найти турниры другой страны

```python
import urllib.request, json

# 1. Найти country_id
data = json.loads(urllib.request.urlopen(
    urllib.request.Request("https://api.rating.chgk.net/countries",
    headers={"accept": "application/json"})
).read())
# Ищем нужную страну в списке

# 2. Найти города
towns = json.loads(urllib.request.urlopen(
    urllib.request.Request("https://api.rating.chgk.net/towns?country={COUNTRY_ID}",
    headers={"accept": "application/json"})
).read())

# 3. Найти турниры по городу
tournaments = json.loads(urllib.request.urlopen(
    urllib.request.Request("https://api.rating.chgk.net/tournaments?town={TOWN_ID}&page=1",
    headers={"accept": "application/json"})
).read())
```

## Как добавить новый год

1. Найти ID нового турнира: `tournaments?name=Великобритан` или на сайте rating.chgk.info
2. Добавить ID в `CHVB_IDS` в `fetch_data.py` и `TOURNAMENT_IDS` в `build_stats.py`
3. Если нужны ручные оверрайды зачёта -- добавить в `VNE_ZACHETA` / `V_ZACHETE` в `build_stats.py`
4. Запустить `python3 fetch_data.py && python3 build_stats.py && cp chvb_stats.html index.html`

## Существующие парсеры

- [maii-chgk/rating-scraper](https://github.com/maii-chgk/rating-scraper) -- Django + Postgres, полный парсер всех турниров (Python)
- [bodrovis/rating-chgk-v2](https://github.com/bodrovis/rating-chgk-v2) -- Ruby SDK с документацией по API
- `chgk_rating` -- Dart-пакет (pub.dev)

## Структура проекта

```
chgk_parser/
  build_stats.py          # Генератор HTML из JSON-данных
  fetch_data.py           # Парсер API (скачивание данных)
  index.html              # = chvb_stats.html (для GitHub Pages)
  chvb_stats.html         # Сгенерированная страница
  data/
    chvb_results.json     # Сырые данные всех ЧВБ (турниры + результаты + составы)
    players_stats.json    # Агрегированная статистика по игрокам
    teams_stats.json      # Агрегированная статистика по командам
    all_uk_tournaments.json  # Все турниры в UK (не только ЧВБ)
    uk_towns.json         # Список городов UK
```
