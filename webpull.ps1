$ErrorActionPreference = 'Stop'

$releaseRoot = 'https://github.com/Exo2v/indigo-otter-731/releases/download/lasso1'
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
Settings includes a small Diagnostics button for the live log; it opens only when
clicked and never saves a log unless you choose Save.
A new config has a blank API-key value and defaults to
google/gemma-4-31b-it:free; screenshot upload consent is off. The model is not
shown in the Settings GUI. Only the two allowlisted Gemma :free vision models
are accepted; paid model IDs are rejected.

Enter your own API key and enable consent only if you agree to send screenshots
through OpenRouter to its free-model host. Host data terms apply; do not upload
sensitive screens.

Config path: %APPDATA%\LassV7\config.json
To change the model, open this config file and edit models.openrouter to an
allowlisted Gemma :free ID, then restart LassV7. The app does not read
credentials from this download folder.
No servomotor/credential file is bundled.
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
