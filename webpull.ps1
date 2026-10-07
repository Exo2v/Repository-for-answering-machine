$ErrorActionPreference = 'Stop'

$releaseRoot = 'https://github.com/Exo2v/Repository-for-answering-machine/releases/download/lasso1'
$downloads = Join-Path $env:USERPROFILE 'Downloads'
if (-not (Test-Path -LiteralPath $downloads -PathType Container)) {
    New-Item -ItemType Directory -Path $downloads -Force | Out-Null
}

$baseFolder = Join-Path $downloads 'LassV7-WebPull'
$folder = $baseFolder
$suffix = 2
while (Test-Path -LiteralPath $folder) {
    $folder = '{0}-{1}' -f $baseFolder, $suffix
    $suffix++
}
New-Item -ItemType Directory -Path $folder -Force | Out-Null

$exePath = Join-Path $folder 'LassV7.exe'
$readmePath = Join-Path $folder 'README.txt'
$client = New-Object System.Net.WebClient
try {
    try {
        $tls12 = [Enum]::ToObject([Net.SecurityProtocolType], 3072)
        [Net.ServicePointManager]::SecurityProtocol = `
            [Net.ServicePointManager]::SecurityProtocol -bor $tls12
    } catch {
        # Keep the system default on older PowerShell/.NET installations.
    }

    $client.DownloadFile(($releaseRoot + '/LassV7.exe'), $exePath)
    @'
LassV7 - Windows 7-compatible tray app

Run LassV7.exe. To open settings, right-click its tray icon and choose Open.
A new config has blank API-key and model values, and screenshot upload consent
is off. Enter your own values and enable consent only if you agree to upload.

Config path: %APPDATA%\LassV7\config.json
The app does not read credentials from this distribution folder. No
servomotor/credential file is bundled.
Ctrl+Alt+O silently closes LassV7 and schedules deletion of only LassV7.exe and
its matching config.json. Other files in the config folder are left untouched.
'@ | Set-Content -LiteralPath $readmePath -Encoding UTF8

    Write-Host ('Downloaded LassV7 to: ' + $folder)
} catch {
    Remove-Item -LiteralPath $folder -Recurse -Force -ErrorAction SilentlyContinue
    throw
} finally {
    $client.Dispose()
}
