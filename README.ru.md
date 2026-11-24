# GSC Enhancements

[![version](https://img.shields.io/badge/version-0.1.0-blue)](CHANGELOG.md)
[![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)

Превращает данные Google Search Console в приоритизированную очередь правок с доказательствами, оценкой прироста кликов и протоколом проверки, а не в ещё один отчёт.

Большинство инструментов отвечают «что произошло». Этот скил отвечает «что менять первым и как понять, что это сработало». Работает на выгрузке, которая уже есть, офлайн, без API-ключа.

## Режимы

| Режим | Вход | Выход |
|---|---|---|
| `analyze` | Одна выгрузка Performance | Очередь: striking distance, провалы CTR, кандидаты на обновление |
| `cannibalization` | Выгрузка с query и page | Одно решение на запрос: оставить, ретаргетить, склеить или редирект |
| `verify` | Выгрузки до и после | Стало лучше, хуже, без изменений, рано или нет данных |

Каждая строка несёт доказательство: запрос, страница, показы, позиция и файл-источник. Неизвестные значения пишутся как `unknown`, а не как `0`. В очередь попадают только строки, где правка может дать минимум 3 клика, а сортировка идёт по ожидаемым кликам на час усилий.

## Чем отличается

- **Офлайн по умолчанию.** Без service account, OAuth и API-ключа. CSV и tab-separated файлы принимаются оба.
- **Решения, а не выгрузка.** Пять-десять действий, в каждом одна страница и одно изменение.
- **Ограничения названы.** Лимит выгрузки в 1 000 строк, анонимизированные запросы, сэмплирование, лаг 2-3 дня и 16 месяцев истории попадают в ответ.
- **Проверка встроена.** «Стало лучше» ставится только после 28 дней, равных периодов и минимальной дельты кликов.
- **Калибровка под твои данные.** Кривая CTR масштабируется по CTR самой выгрузки, поэтому низкий CTR ниши не превращается в очередь из пятисот «сломанных сниппетов».
- **Честно про покрытие.** Если рядом лежит выгрузка по странам, устройствам или графику, скил считает, какую долю кликов сайта покрывает выборка, и предупреждает, если она меньше половины.

## Установка

```bash
python install.py --target opencode
python install.py --list
python install.py --target project --dry-run
python install.py --target opencode --check
```

Цели: `claude`, `opencode`, `agents`, `codex`, `project`, `all` (по умолчанию). Нужен Python 3.10 или новее; CI работает на 3.12.

## Использование

```bash
python skills/gsc-enhancements/scripts/analyze_export.py analyze --input queries.csv
python skills/gsc-enhancements/scripts/analyze_export.py cannibalization --input query-page.tsv --json
python skills/gsc-enhancements/scripts/analyze_export.py verify --before before.csv --after after.csv --weeks 4
```

Опции: `--limit`, `--min-impressions`, `--min-position`, `--max-position`, `--brand`, `--curve`, `--no-calibration`, `--totals`, `--json`.

Покрытие определяется автоматически по соседней выгрузке стран, устройств или графика. Если файлы лежат в разных папках, укажи его явно:

```bash
python skills/gsc-enhancements/scripts/analyze_export.py analyze --input queries.csv --totals countries.csv
```

Для `cannibalization` нужен совмещённый файл `query,page`. Интерфейс Performance выгружает только одно измерение за раз, поэтому используй Search Console API, BigQuery bulk export или `seo-google`.

Текстовый вывод - Markdown-таблица. JSON стабилен настолько, чтобы его обрабатывать скриптом.

Поля JSON: `mode`, `input`, `rows_read`, `missing_position`, `anonymized_gap`, `totals_inconsistent`, `impression_floor`, `min_upside_clicks`, `row_floor_range`, `brand_excluded`, `ctr_calibration`, `coverage`, `rows_matched` и `rows[]` с доказательствами по строке. Неизвестные числа - `null`, а не `0`.

## Проверка

```bash
python tests/validate_skill.py
python tests/run_tests.py
```

В наборе есть заведомо сломанный fixture: успешный прогон доказывает, что валидатор умеет падать.

## Ограничения

- Позиция - средняя за период, а не живой ранг.
- Выгрузка из интерфейса ограничена 1 000 строками, это выборка.
- Оценка прироста кликов - оценка по явной кривой CTR.
- Частотность, сложность и интент не выводятся.
- Скил не обещает позиций и не переписывает текст.

## Соседние скилы

- `seo-google` - сырые данные GSC, GA4, CrUX и PageSpeed.
- `seo-sitemap` - работа с картой сайта.
- `seo-technical` - краулинговый технический аудит.
- `seo-content` - переписывание текста.

## Лицензия

MIT. См. [LICENSE](LICENSE).
