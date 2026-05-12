#!/usr/bin/env bash

set -e

usage() {
  echo "Usage: $(basename "$0") [-h] [usb|fw|auto]"
  echo ""
  echo "Перезапускает docker compose окружение с нужным устройством камеры."
  echo ""
  echo "Аргументы:"
  echo "  usb   Использовать USB-камеру (XIMEA, Vendor ID 0x20f7)"
  echo "  fw    Использовать FireWire-камеру (/dev/fw1)"
  echo "  auto  Определить устройство автоматически (по умолчанию)"
  echo ""
  echo "Опции:"
  echo "  -h    Показать эту справку и выйти"
}

if [ "${1:-}" = "-h" ]; then
  usage
  exit 0
fi

DEVICE_TYPE="${1:-auto}"
FW_DEV="/dev/fw1"

if [ "$DEVICE_TYPE" = "auto" ]; then
  # USB: ищем XIMEA по Vendor ID 0x20f7 (не зависит от номера порта)
  HAS_USB=false
  HAS_FW=false
  lsusb 2>/dev/null | grep -qi "20f7" && HAS_USB=true
  [ -e "$FW_DEV" ] && HAS_FW=true

  if $HAS_FW && ! $HAS_USB; then
    DEVICE_TYPE="fw"
    echo "[auto] Обнаружено FireWire-устройство: $FW_DEV"
  elif $HAS_USB && ! $HAS_FW; then
    DEVICE_TYPE="usb"
    echo "[auto] Обнаружена USB-камера XIMEA (via lsusb)"
  elif $HAS_USB && $HAS_FW; then
    echo "[auto] Обнаружены оба устройства (USB и FireWire). Укажите тип явно: $0 <usb|fw>"
    exit 1
  else
    echo "[auto] Устройства не найдены (XIMEA USB 0x20f7, $FW_DEV). Проверьте подключение или укажите тип явно: $0 <usb|fw>"
    exit 1
  fi
fi

case "$DEVICE_TYPE" in
  usb)
    # USB: камера доступна через /dev/bus/usb volume в docker-compose.yml.
    # XIMEA_CAMERA_DEVICE не нужна — дефолт /dev/null в compose безвреден.
    unset XIMEA_CAMERA_DEVICE
    echo "[usb] Используется /dev/bus/usb volume (автоматически любой порт)"
    ;;
  fw)
    export XIMEA_CAMERA_DEVICE="$FW_DEV:$FW_DEV"
    echo "[fw] Используется FireWire: $FW_DEV"
    ;;
  *)
    echo "Usage: $0 [usb|fw|auto]"
    exit 1
    ;;
esac

export COMPOSE_BAKE=true

cd /home/robotom/workspace/xtomo/rbtm-drivers-next && \
docker compose down && \
docker compose build && \
docker compose up -d experiment redis tomograph_server
