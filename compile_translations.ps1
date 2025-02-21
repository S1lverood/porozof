$languages = Get-ChildItem -Path "bot/locale" -Directory

foreach ($lang in $languages) {
    Write-Host "Compiling $($lang.Name) translations..."
    docker exec vpnporozoff-vpn_hub_bot-1 msgfmt -o /app/bot/locale/$($lang.Name)/LC_MESSAGES/bot.mo /app/bot/locale/$($lang.Name)/LC_MESSAGES/bot.po
}

Write-Host "Compilation finished."
