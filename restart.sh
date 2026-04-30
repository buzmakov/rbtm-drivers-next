#!/usr/bin/env bash

set -e

usage() {
  echo "Usage: $(basename "$0") [-h] [usb|fw|auto]"
  echo ""
  echo "Перезапускает docker compose окружение с нужным устройством камеры."
  echo ""
  echo "Аргументы:"
  echo "  usb   Использовать USB-камеру        (/dev/bus/usb/004/003)"
  echo "  fw    Использовать FireWire-камеру   (/dev/fw1)"
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

USB_DEV="/dev/bus/usb/004/003"
FW_DEV="/dev/fw1"

if [ "$DEVICE_TYPE" = "auto" ]; then
  HAS_USB=false
  HAS_FW=false
  [ -e "$USB_DEV" ] && HAS_USB=true
  [ -e "$FW_DEV" ]  && HAS_FW=true

  if $HAS_FW && ! $HAS_USB; then
    DEVICE_TYPE="fw"
    echo "[auto] Обнаружено FireWire-устройство: $FW_DEV"
  elif $HAS_USB && ! $HAS_FW; then
    DEVICE_TYPE="usb"
    echo "[auto] Обнаружено USB-устройство: $USB_DEV"
  elif $HAS_USB && $HAS_FW; then
    echo "[auto] Обнаружены оба устройства (USB и FireWire). Укажите тип явно: $0 <usb|fw>"
    exit 1
  else
    echo "[auto] Устройства не найдены ($USB_DEV, $FW_DEV). Проверьте подключение или укажите тип явно: $0 <usb|fw>"
    exit 1
  fi
fi

case "$DEVICE_TYPE" in
  usb)
    export XIMEA_CAMERA_DEVICE="$USB_DEV:$USB_DEV"
    ;;
  fw)
    export XIMEA_CAMERA_DEVICE="$FW_DEV:$FW_DEV"
    ;;
  *)
    echo "Usage: $0 [usb|fw|auto]"
    echo "  usb   — USB camera        ($USB_DEV)"
    echo "  fw    — FireWire camera   ($FW_DEV)"
    echo "  auto  — определить автоматически (по умолчанию)"
    exit 1
    ;;
esac

export COMPOSE_BAKE=true

cd /home/robotom/workspace/xtomo/rbtm-drivers-next && \
docker compose down && \
docker compose build && \
docker compose up experiment redis tomograph_server
