# Отправка одной карточки в Telegram прямо с компьютера, минуя GitHub.
# Нужно, когда хочется получить конкретное место вне очереди или проверить,
# как выглядит новая карточка.
#
#   powershell -File scripts/Send-Card.ps1 -Id petra -Token "8123:AA..."
#
# Внимание: этот скрипт НЕ отмечает место как отправленное в data/log.json,
# поэтому оно всё равно придёт в свой день по расписанию. Для обычной
# ежедневной рассылки работает send_daily.py на GitHub Actions.

param(
    [Parameter(Mandatory = $true)][string]$Id,
    [Parameter(Mandatory = $true)][string]$Token,
    [string]$ChatId = "409958314"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$cardPath = Join-Path $root "cards/$Id.json"
if (-not (Test-Path $cardPath)) { throw "Нет карточки: $cardPath" }
$c = Get-Content -Raw -Encoding UTF8 $cardPath | ConvertFrom-Json

function Esc($t) {
    if ($null -eq $t) { return "" }
    return ([string]$t).Replace('&', '&amp;').Replace('<', '&lt;').Replace('>', '&gt;')
}

function Send-Api($method, $payload) {
    $json = $payload | ConvertTo-Json -Depth 12 -Compress
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
    $uri = "https://api.telegram.org/bot$Token/$method"
    return Invoke-RestMethod -Uri $uri -Method Post -Body $bytes -ContentType "application/json; charset=utf-8"
}

# ── альбом фотографий ────────────────────────────────────────────────
$caption = "<b>$((Esc $c.ru).ToUpper())</b> · $(Esc $c.country)"
if ($c.lead) { $caption += "`n<i>$(Esc $c.lead)</i>" }

$photos = @($c.photos | Where-Object { $_.url } | Select-Object -First 10)
if ($photos.Count -gt 0) {
    $media = @()
    for ($i = 0; $i -lt $photos.Count; $i++) {
        $item = @{ type = "photo"; media = $photos[$i].url }
        if ($i -eq 0) { $item.caption = $caption; $item.parse_mode = "HTML" }
        $media += $item
    }
    Send-Api "sendMediaGroup" @{ chat_id = $ChatId; media = $media } | Out-Null
    Write-Host "  фото отправлено: $($photos.Count)"
    Start-Sleep -Seconds 2
}

# ── текстовые блоки ──────────────────────────────────────────────────
$blocks = New-Object System.Collections.ArrayList

$title = "<b>$((Esc $c.ru).ToUpper())</b> · $(Esc $c.country)"
if ($c.status) { $title += "`n<i>$(Esc $c.status)</i>" }
[void]$blocks.Add($title)

foreach ($p in $c.why) { [void]$blocks.Add((Esc $p)) }

if ($c.must_see) {
    $s = "🎯 <b>ЧТО ИМЕННО СМОТРЕТЬ</b>"
    foreach ($m in $c.must_see) {
        $s += "`n`n<b>$(Esc $m.name)</b>`n$(Esc $m.what)"
        if ($m.tip) { $s += "`n<i>↳ $(Esc $m.tip)</i>" }
    }
    [void]$blocks.Add($s)
}

if ($c.hacks) {
    $s = "🧭 <b>ЛАЙФХАКИ</b>"
    foreach ($h in $c.hacks) {
        $s += "`n`n• $(Esc $h.tip)"
        if ($h.src) { $s += " <a href=""$(Esc $h.src)"">·источник</a>" }
    }
    [void]$blocks.Add($s)
}

if ($c.season) {
    $s = "🗓 <b>КОГДА ЕХАТЬ</b>"
    if ($c.season.best) { $s += "`n<b>Лучшее время:</b> $(Esc $c.season.best)" }
    if ($c.season.avoid) { $s += "`n<b>Не стоит:</b> $(Esc $c.season.avoid)" }
    if ($c.season.daily) { $s += "`n<b>По часам:</b> $(Esc $c.season.daily)" }
    [void]$blocks.Add($s)
}

if ($c.safety) {
    $s = "🛡 <b>БЕЗОПАСНОСТЬ</b>"
    if ($c.safety.status) { $s += "`n<b>$(Esc $c.safety.status)</b>" }
    if ($c.safety.text) { $s += "`n$(Esc $c.safety.text)" }
    foreach ($p in $c.safety.points) { $s += "`n• $(Esc $p)" }
    [void]$blocks.Add($s)
}

if ($c.know) {
    $s = "📋 <b>ЧТО НУЖНО ЗНАТЬ</b>"
    foreach ($k in $c.know) { $s += "`n`n<b>$(Esc $k.label):</b> $(Esc $k.text)" }
    [void]$blocks.Add($s)
}

if ($c.cinema) {
    $s = "🎬 <b>ЗДЕСЬ СНИМАЛИ</b>"
    foreach ($f in $c.cinema) {
        $year = if ($f.year) { " ($(Esc $f.year))" } else { "" }
        $s += "`n`n• <b>$(Esc $f.title)</b>$year — $(Esc $f.note)"
    }
    [void]$blocks.Add($s)
}

if ($c.facts) {
    $s = "💡 <b>ЧЕГО ПОЧТИ НИКТО НЕ ЗНАЕТ</b>"
    foreach ($f in $c.facts) { $s += "`n`n• $(Esc $f)" }
    [void]$blocks.Add($s)
}

if ($c.logistics) {
    $s = "🧳 <b>ПРАКТИКА</b>"
    if ($c.logistics.days) { $s += "`n<b>Сколько дней:</b> $(Esc $c.logistics.days)" }
    if ($c.logistics.how) { $s += "`n<b>Как добраться:</b> $(Esc $c.logistics.how)" }
    if ($c.logistics.base) { $s += "`n<b>Где базироваться:</b> $(Esc $c.logistics.base)" }
    if ($c.logistics.money) { $s += "`n<b>Деньги:</b> $(Esc $c.logistics.money)" }
    [void]$blocks.Add($s)
}

if ($c.route) { [void]$blocks.Add("🧩 <b>КАК ВСТРОИТЬ В МАРШРУТ</b>`n$(Esc $c.route)") }

if ($c.sources) {
    $links = ($c.sources | ForEach-Object { "<a href=""$(Esc $_.url)"">$(Esc $_.title)</a>" }) -join ", "
    [void]$blocks.Add("📚 <b>Откуда всё это:</b> $links")
}

# ── склейка в сообщения по 4096 символов ─────────────────────────────
$messages = New-Object System.Collections.ArrayList
$current = ""
foreach ($b in $blocks) {
    $candidate = if ($current) { "$current`n`n$b" } else { $b }
    if ($candidate.Length -le 4096) {
        $current = $candidate
    } else {
        if ($current) { [void]$messages.Add($current) }
        $current = $b
    }
}
if ($current) { [void]$messages.Add($current) }

foreach ($m in $messages) {
    Send-Api "sendMessage" @{
        chat_id              = $ChatId
        text                 = $m
        parse_mode           = "HTML"
        link_preview_options = @{ is_disabled = $true }
    } | Out-Null
    Start-Sleep -Seconds 1
}

Write-Host "Отправлено: $($c.ru) — $($photos.Count) фото, $($messages.Count) сообщений"
