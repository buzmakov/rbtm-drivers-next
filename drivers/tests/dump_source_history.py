"""Дамп внутренних журналов генератора ISOVOLT 3003 (только чтение).

Читает идентификацию, наработку, слова состояния, текущую ошибку и
журналы операций (``HO``) и прогревов (``HW``) — см. руководство
``vendor/docs/ISOVOLT_3003_manual_rus.pdf``, раздел 8 (стр. 36–44).
Высокое напряжение НЕ включается, никакие параметры не меняются.

Порт не открывается заново: используется общий экземпляр
``HWSource.get_shared()``, поэтому скрипт можно запускать в том же
процессе, что и драйвер, не создавая второй файловый дескриптор на
том же tty (каждое открытие дёргает DTR/RTS генератора).

Запуск на robotom (порт уже проброшен в контейнер, UI должен быть неактивен,
чтобы опросы не вклинивались в обмен):

    docker exec rbtm-tomograph-server python /xtomo/drivers/tests/dump_source_history.py
    docker exec rbtm-tomograph-server python /xtomo/drivers/tests/dump_source_history.py --max-records 128

Формат ответов генератора: ``*<данные>{CR}`` на запрос, ``#<данные>{CR}`` —
асинхронно (например, код ошибки при её возникновении). Скрипт печатает
все строки как есть (``raw``), ничего не интерпретируя, кроме SR:12.
"""
import argparse
import os
import sys
import time

# Скрипт запускают как файл (python drivers/tests/dump_source_history.py),
# поэтому пакет drivers нужно найти по пути репозитория.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from drivers.XRaySource.XRaySource import HWSource  # noqa: E402

IDLE_TIMEOUT = 0.7      # с: тишина, после которой считаем ответ законченным


def get_source(port=None):
    """Вернуть общий экземпляр драйвера (порт берётся из конфига, если не задан)."""
    if port is None:
        from drivers.utils import get_source_config
        port = get_source_config()['port']
    return HWSource.get_shared(port)


def query(source, command):
    """Отправить команду и вернуть список всех строк ответа (без CR).

    Работает через транспорт ``HWSource``: запись и чтение — под его
    ``_port_lock``, так что параллельный опрос драйвера не вклинится
    в середину обмена. Журналы ``HO``/``HW`` отвечают несколькими
    строками, поэтому читаем до тишины, а не ровно одну строку.
    """
    lines = []
    with source._port_lock:
        source._write_command(command)
        deadline = time.time() + IDLE_TIMEOUT
        while True:
            raw = source.serial_port.read_until(b'\r')
            if raw:
                lines.append(raw.decode('latin-1').strip())
                deadline = time.time() + IDLE_TIMEOUT
                continue
            if time.time() >= deadline:
                break
    return lines


def show(source, command, label=None):
    lines = query(source, command)
    text = ' | '.join(lines) if lines else '<no response>'
    print('{:<10} {:<28} {}'.format(command, label or '', text))
    return lines


def dump_journal(source, prefix, label, max_records):
    """Читать записи журнала prefix:001..max_records, пока генератор отвечает."""
    print('\n== {} ({}:001..{:03d}) =='.format(label, prefix, max_records))
    empty_streak = 0
    for n in range(1, max_records + 1):
        lines = query(source, '{}:{:03d}'.format(prefix, n))
        if not lines:
            empty_streak += 1
            if empty_streak >= 3:
                print('  ... no response for 3 records in a row, stop')
                break
            continue
        empty_streak = 0
        print('  {:03d}: {}'.format(n, ' | '.join(lines)))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--port', default=None,
                        help='путь к порту; по умолчанию — из конфига источника')
    parser.add_argument('--max-records', type=int, default=32,
                        help='сколько записей журналов HO/HW читать (макс. 128)')
    parser.add_argument('--no-journals', action='store_true',
                        help='только статус, без журналов HO/HW')
    args = parser.parse_args()

    source = get_source(args.port)
    print('ISOVOLT 3003 read-only dump, port {}, {}'.format(
        source.tty_name, time.strftime('%Y-%m-%d %H:%M:%S')))

    show(source, 'ID', 'software id')
    show(source, 'XT', 'tube name')
    show(source, 'XU', 'tube nominal kV/A/W')
    show(source, 'RH', 'hours: unit + tube')
    show(source, 'RH:0', 'hours: unit')
    show(source, 'RH:1', 'hours: current tube')
    show(source, 'VN', 'nominal kV x1000')
    show(source, 'VA', 'actual kV x1000')
    show(source, 'CN', 'nominal mA x1000')
    show(source, 'CA', 'actual mA x1000')
    for word in ('01', '06', '12', '30'):
        lines = show(source, 'SR:' + word, 'status word ' + word)
        if word == '12' and lines:
            try:
                code = int(lines[0].lstrip('*#'))
            except ValueError:
                continue
            print('           -> error code {}: {}'.format(
                code, 'no error' if code == 0 else HWSource.describe_code(code)))
    show(source, 'ER', 'error text')
    show(source, 'RP', 'tube output power')
    show(source, 'PA', 'current program number')

    if not args.no_journals:
        dump_journal(source, 'HO', 'operations journal', args.max_records)
        dump_journal(source, 'HW', 'warm-up journal', args.max_records)


if __name__ == '__main__':
    main()
