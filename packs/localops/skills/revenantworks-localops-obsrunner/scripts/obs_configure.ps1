<#
.SYNOPSIS
  obsrunner's one-command OBS WebSocket setup. The OWNER runs it, once, with OBS closed.

.DESCRIPTION
  Owner rule (2026-10-16): the WebSocket password never sits in a plain environment variable as
  its home, and nothing here ever prints it. The home is a DPAPI file (current user, the estate's
  format: hex of CryptProtectData over UTF-16-LE text, no entropy):

      %LOCALAPPDATA%\estate-secrets\OBS_WEBSOCKET_PASSWORD.dpapi

  obs_ws.py reads that file first (scripts/obs_secret.py), the environment only as a fallback.

  Default (no switch): generates a 32-character password, writes it into OBS's obs-websocket
  config with the server enabled and authentication on (this is the step the WebSocket dialog's
  Apply button does; closing the dialog with OK alone once left the server off), and writes the
  DPAPI file. OBS must be closed: OBS rewrites its config on exit.

  -Migrate: moves an existing plain user variable OBS_WEBSOCKET_PASSWORD into the DPAPI file and
  deletes the variable. OBS's own config is untouched. An empty variable is refused (a masked
  prompt once saved an empty value that read as "no password").

  -Check: says which homes exist (DPAPI file, user variable, OBS config) - never a value.

  Then: python scripts/obs_secret.py where (prints the source, never the value), start OBS, and
  python scripts/obs_ws.py status.

.NOTES
  The obs-websocket 5.x config keys used (server_enabled, auth_required, server_password,
  server_port) are as documented for OBS 28+; -Check prints the keys it found before you change
  anything. Run from PowerShell 7: pwsh -NoProfile -File scripts\obs_configure.ps1 [-Migrate|-Check]
#>
[CmdletBinding()]
param([switch]$Migrate, [switch]$Check)
$ErrorActionPreference = 'Stop'

$Name = 'OBS_WEBSOCKET_PASSWORD'
$SecretDir = Join-Path $env:LOCALAPPDATA 'estate-secrets'
$SecretFile = Join-Path $SecretDir "$Name.dpapi"
$ObsConfig = Join-Path $env:APPDATA 'obs-studio\plugin_config\obs-websocket\config.json'

function Write-Secret([string]$Value) {
    if ([string]::IsNullOrEmpty($Value)) { throw 'refused: the value is empty; nothing was written' }
    Add-Type -AssemblyName System.Security
    $bytes = [Security.Cryptography.ProtectedData]::Protect(
        [Text.Encoding]::Unicode.GetBytes($Value), $null, 'CurrentUser')
    New-Item -ItemType Directory -Force $SecretDir | Out-Null
    [IO.File]::WriteAllText($SecretFile, [Convert]::ToHexString($bytes))
    # Read it back and compare, so a bad write never passes as done.
    $back = [Text.Encoding]::Unicode.GetString([Security.Cryptography.ProtectedData]::Unprotect(
        [Convert]::FromHexString([IO.File]::ReadAllText($SecretFile).Trim()), $null, 'CurrentUser'))
    if ($back -ne $Value) { throw 'refused: the DPAPI file did not read back; check it by hand' }
}

if ($Check) {
    $userVar = [Environment]::GetEnvironmentVariable($Name, 'User')
    $keys = if (Test-Path $ObsConfig) { ((Get-Content -Raw $ObsConfig | ConvertFrom-Json).PSObject.Properties.Name) -join ', ' } else { 'no config file' }
    [ordered]@{
        dpapi_file = (Test-Path $SecretFile)
        user_variable = (-not [string]::IsNullOrEmpty($userVar))
        obs_config = $ObsConfig
        obs_config_keys = $keys
    } | ConvertTo-Json
    return
}

if ($Migrate) {
    $value = [Environment]::GetEnvironmentVariable($Name, 'User')
    if ([string]::IsNullOrEmpty($value)) { throw "refused: no user variable $Name to migrate (or it is empty)" }
    Write-Secret $value
    [Environment]::SetEnvironmentVariable($Name, $null, 'User')
    Remove-Item "Env:$Name" -ErrorAction SilentlyContinue
    "migrated: DPAPI file written and read back; user variable $Name deleted. Restart Claude so no session holds the old value."
    return
}

if (Get-Process obs64, obs32 -ErrorAction SilentlyContinue) { throw 'refused: close OBS first (it rewrites its config on exit)' }
$alphabet = [char[]]'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789'
$rng = [Security.Cryptography.RandomNumberGenerator]::Create()
$buf = [byte[]]::new(32); $rng.GetBytes($buf)
$password = -join ($buf | ForEach-Object { $alphabet[$_ % $alphabet.Length] })

$cfg = if (Test-Path $ObsConfig) { Get-Content -Raw $ObsConfig | ConvertFrom-Json -AsHashtable } else { @{} }
$cfg['server_enabled'] = $true
$cfg['auth_required'] = $true
$cfg['server_password'] = $password
if (-not $cfg.ContainsKey('server_port')) { $cfg['server_port'] = 4455 }
New-Item -ItemType Directory -Force (Split-Path $ObsConfig) | Out-Null
if (Test-Path $ObsConfig) { Copy-Item $ObsConfig "$ObsConfig.bak" -Force }
$cfg | ConvertTo-Json | Set-Content -Encoding utf8 $ObsConfig
Write-Secret $password
$password = $null
"configured: obs-websocket enabled with authentication on port $($cfg['server_port']); password written to OBS's config and the DPAPI file (never printed). Previous OBS config kept as config.json.bak. Next: start OBS, then python scripts\obs_ws.py status."
