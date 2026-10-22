#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
PLIST_NAME="com.matthew.modembattery.plist"
TARGET="$HOME/Library/LaunchAgents/$PLIST_NAME"

echo "در حال فعال‌سازی اجرای خودکار با روشن شدن سیستم..."

# Unload previous version if exists
launchctl bootout "gui/$(id -u)/com.matthew.modembattery" 2>/dev/null || launchctl unload "$TARGET" 2>/dev/null

# Copy plist to LaunchAgents
cp "$DIR/$PLIST_NAME" "$TARGET"

# Load new agent
launchctl bootstrap "gui/$(id -u)" "$TARGET" 2>/dev/null || launchctl load "$TARGET"

echo "✅ با موفقیت فعال شد! آیکون باتری مودم به نوار منوی مک (بالا سمت راست) اضافه شد."
