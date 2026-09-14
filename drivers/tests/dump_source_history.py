"""Дамп внутренних журналов генератора ISOVOLT 3003 (только чтение).

Читает идентификацию, наработку, слова состояния, текущую ошибку и
журналы операций (``HO``) и прогревов (``HW``) — см. руководство
``vendor/docs/ISOVOLT_3003_manual_rus.pdf``, раздел 8 (стр. 36–44).
Высокое напряжение НЕ включается, никакие параметры не меняются.

Запуск на robotom (порт уже проброшен в контейнер, UI должен быть неактивен,
чтобы опросы не вклинивались в обмен):

    docker exec rbtm-tomograph-server python /xtomo/drivers/tests/dump_source_history.py
    docker exec rbtm-tomograph-server python /xtomo/drivers/tests/dump_source_history.py --max-records 128

Формат ответов генератора: ``*<данные>{CR}`` на запрос, ``#<данные>{CR}`` —
асинхронно (например, код ошибки при её возникновении). Скрипт печатает
все строки как есть (``raw``), ничего не интерпретируя, кроме SR:12.
"""
import argparse
import sys
import time

import serial

DEFAULT_PORT = '/dev/ttyUSB0'
LINE_TIMEOUT = 2.0      # с: ожидание первой строки ответа
IDLE_TIMEOUT = 0.7      # с: тишина, после которой считаем ответ законченным

# Коды ошибок из руководства (стр. 44–47); полный словарь — HWSource.STATUS_STRINGS
try:
    sys.path.insert(0, '/xtomo')
    from drivers.XRaySource.XRaySource import HWSource
    STATUS_STRINGS = HWSource.STATUS_STRINGS
except Exception:
    STATUS_STRINGS = {}


def open_port(port):
    return serial.Serial(
        port, baudrate=9600, bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
        timeout=LINE_TIMEOUT, rtscts=False, dsrdtr=True,
    )


def query(ser, command):
    """Отправить команду и вернуть список всех строк ответа (без CR)."""
    ser.reset_input_buffer()
    ser.write((command + '\r\n').encode())
    ser.flush()
    lines = []
    deadline = time.time() + LINE_TIMEOUT
    while True:
        raw = ser.read_until(b'\r')
        if raw:
            lines.append(raw.decode('latin-1').strip())
            deadline = time.time() + IDLE_TIMEOUT
            continue
        if time.time() >= deadline:
            break
    return lines


def show(ser, command, label=None):
    lines = query(ser, command)
    text = ' | '.join(lines) if lines else '<no response>'
    print('{:<10} {:<28} {}'.format(command, label or '', text))
    return lines


def dump_journal(ser, prefix, label, max_records):
    """Читать записи журнала prefix:001..max_records, пока генератор отвечает."""
    print('\n== {} ({}:001..{:03d}) =='.format(label, prefix, max_records))
    empty_streak = 0
    for n in range(1, max_records + 1):
        lines = query(ser, '{}:{:03d}'.format(prefix, n))
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
    parser.add_argument('--port', default=DEFAULT_PORT)
    parser.add_argument('--max-records', type=int, default=32,
                        help='сколько записей журналов HO/HW читать (макс. 128)')
    parser.add_argument('--no-journals', action='store_true',
                        help='только статус, без журналов HO/HW')
    args = parser.parse_args()

    print('ISOVOLT 3003 read-only dump, port {}, {}'.format(
        args.port, time.strftime('%Y-%m-%d %H:%M:%S')))
    with open_port(args.port) as ser:
        time.sleep(0.5)
        show(ser, 'ID', 'software id')
        show(ser, 'XT', 'tube name')
        show(ser, 'XU', 'tube nominal kV/A/W')
        show(ser, 'RH', 'hours: unit + tube')
        show(ser, 'RH:0', 'hours: unit')
        show(ser, 'RH:1', 'hours: current tube')
        show(ser, 'VN', 'nominal kV x1000')
        show(ser, 'VA', 'actual kV x1000')
        show(ser, 'CN', 'nominal mA x1000')
        show(ser, 'CA', 'actual mA x1000')
        for word in ('01', '06', '12', '30'):
            lines = show(ser, 'SR:' + word, 'status word ' + word)
            if word == '12' and lines:
                try:
                    code = int(lines[0].lstrip('*#'))
                    print('           -> error code {}: {}'.format(
                        code, STATUS_STRINGS.get(code, 'no error' if code == 0 else 'unknown')))
                except ValueError:
                    pass
        show(ser, 'ER', 'error text')
        show(ser, 'PA', 'current program number')

        if not args.no_journals:
            dump_journal(ser, 'HO', 'operations journal', args.max_records)
            dump_journal(ser, 'HW', 'warm-up journal', args.max_records)


if __name__ == '__main__':
    main()
