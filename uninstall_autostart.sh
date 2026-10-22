#!/bin/bash
PLIST_NAME="com.matthew.modembattery.plist"
TARGET="$HOME/Library/LaunchAgents/$PLIST_NAME"

echo "در حال غیرفعال‌سازی اجرای خودکار..."

launchctl bootout "gui/$(id -u)/com.matthew.modembattery" 2>/dev/null || launchctl unload "$TARGET" 2>/dev/null
pkill -f "modem_battery_app.py" 2>/dev/null

if [ -f "$TARGET" ]; then
    rm "$TARGET"
fi

echo "✅ برنامه با موفقیت متوقف و از استارتاپ حذف شد."
