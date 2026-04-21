# Hacker News Scraper

CLI-инструмент для парсинга, анализа и мониторинга Hacker News.

## Установка

```bash
pip install -r requirements.txt
```

## Использование

Все команды доступны через единую точку входа `main.py`:

```bash
python3 main.py scrape              # парсинг с настройками из config.json
python3 main.py analyze             # анализ data.json
python3 main.py watch --interval 30 # автоматический запуск каждые 30 мин
python3 main.py config              # показать текущие настройки
```

Каждый скрипт также работает самостоятельно:

```bash
python3 scraper.py                          # использует config.json
python3 scraper.py --limit 20 --min-score 200 --output top.json
python3 analyze.py
```

## Настройки — config.json

```json
{
  "min_score": 100,
  "limit": 30,
  "output_file": "data.json",
  "sources": ["hackernews"]
}
```

Аргументы командной строки имеют приоритет над `config.json`.

## Команды

### `scrape`

Парсит топ-N статей с HN, фильтрует по рейтингу, сохраняет результаты.

| Флаг | По умолчанию | Описание |
|------|-------------|----------|
| `--limit N` | из config | Количество статей |
| `--min-score N` | из config | Минимальный рейтинг |
| `--output FILE` | из config | Имя JSON-файла |

### `analyze`

Читает `data.json` и показывает:
- средний / максимальный / минимальный рейтинг
- самый активный автор
- пиковый час публикаций (UTC)
- гистограмму рейтингов
- **сравнение с предыдущим запуском** — новые статьи, рост/падение рейтингов

### `watch`

Запускает парсер по расписанию. Каждый запуск логируется в `scraper.log`.

```
2026-04-22 10:30:00 run=1 fetched=30 filtered=17 output=data.json
```

### `config`

Выводит содержимое `config.json` и итоговые активные значения.

## Структура проекта

```
news-scraper/
├── main.py          # единая точка входа
├── scraper.py       # парсинг HN
├── parser.py        # фильтрация и сохранение
├── analyze.py       # статистика и сравнение запусков
├── scheduler.py     # запуск по расписанию
├── config.json      # настройки по умолчанию
├── requirements.txt
├── data.json        # последний результат
├── data_prev.json   # предыдущий результат (для сравнения)
├── data.csv         # последний результат в CSV
└── scraper.log      # лог запусков watch
```
