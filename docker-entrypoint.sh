#!/bin/bash
# docker-entrypoint.sh
#
# Создаёт симлинки /dev/ximc/<SERIAL> -> /dev/ttyACM<N> внутри контейнера,
# используя серийные номера контроллеров из sysfs.
#
# Это гарантирует, что xi-com:///dev/ximc/<SERIAL> в devices.cfg всегда
# указывает на правильный контроллер, даже если ttyACM-номер изменился
# после переподключения USB или перезапуска без рестарта хоста.
#
# Запускается как ENTRYPOINT перед основной командой (exec "$@").

set -e

echo "[entrypoint] Creating /dev/ximc symlinks via sysfs..."
mkdir -p /dev/ximc

for ttydev in /dev/ttyACM*; do
    # Пропустить glob, если устройств нет
    [ -e "$ttydev" ] || continue

    ttyname=$(basename "$ttydev")

    # Путь к sysfs-узлу устройства
    sysfs_tty="/sys/class/tty/${ttyname}/device"
    if [ ! -e "$sysfs_tty" ]; then
        echo "  [skip] no sysfs node for $ttyname"
        continue
    fi

    # Перейти к USB-интерфейсу (родителю ACM-устройства), затем к USB-устройству
    usb_iface=$(readlink -f "$sysfs_tty")
    # Серийный номер хранится в ../serial относительно USB-интерфейса
    serial_file="$(dirname "$usb_iface")/serial"
    if [ ! -f "$serial_file" ]; then
        echo "  [skip] no serial file for $ttyname (path: $serial_file)"
        continue
    fi

    # Читаем серийник, убираем пробелы, приводим к верхнему регистру
    serial=$(tr -d '[:space:]' < "$serial_file" | tr '[:lower:]' '[:upper:]')
    if [ -z "$serial" ]; then
        echo "  [skip] empty serial for $ttyname"
        continue
    fi

    echo "  $ttyname -> /dev/ximc/$serial"
    ln -sf "$ttydev" "/dev/ximc/$serial"
done

echo "[entrypoint] /dev/ximc contents:"
ls -la /dev/ximc/ 2>/dev/null || echo "  (empty)"

exec "$@"
