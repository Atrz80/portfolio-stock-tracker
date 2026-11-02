# start-all.ps1 - Start Freellmpool and FastAPI, then wait for them to be healthy.
[CmdletBinding()]
param(
    [int]$GatewayPort = 8080,
    [int]$ApiPort = 8000,
    [int]$TimeoutSeconds = 60
)

$ErrorActionPreference = 'Stop'
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
$WorkDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$LogDir = Join-Path $WorkDir 'logs'
$ManifestPath = Join-Path $WorkDir '.services.json'
$GlobalHome = if ($env:AI_WORKSTATION_HOME) { $env:AI_WORKSTATION_HOME } else { 'E:\Proyectos\ai-workstation' }
$RuntimeRoot = Join-Path $GlobalHome 'runtime'
$Python = Join-Path $RuntimeRoot 'venv\Scripts\python.exe'
$Freellmpool = Join-Path $RuntimeRoot 'venv\Scripts\freellmpool.exe'
$GlobalEnv = Join-Path $GlobalHome '.env'

if (-not (Test-Path -LiteralPath $GlobalEnv)) {
    throw "The global AI configuration was not found: $GlobalEnv"
}
if (-not (Test-Path -LiteralPath $Python)) {
    throw "The global Python runtime was not found on E: $Python"
}
if (-not (Test-Path -LiteralPath $Freellmpool)) {
    throw "Freellmpool was not found in the global runtime on E: $Freellmpool"
}

# Load the shared AI configuration into this process without printing secrets.
Get-Content -LiteralPath $GlobalEnv -Encoding UTF8 | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith('#') -and $line.Contains('=')) {
        $name, $value = $line.Split('=', 2)
        $name = $name.Trim()
        if ($name -match '^[A-Za-z_][A-Za-z0-9_]*$') {
            $cleanValue = $value.Trim()
            if ($cleanValue.Length -ge 2 -and (
                ($cleanValue.StartsWith('"') -and $cleanValue.EndsWith('"')) -or
                ($cleanValue.StartsWith("'") -and $cleanValue.EndsWith("'"))
            )) {
                $cleanValue = $cleanValue.Substring(1, $cleanValue.Length - 2)
            }
            Set-Item -Path "Env:$name" -Value $cleanValue
        }
    }
}

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

function Test-HttpReady {
    param([string]$Url)
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 500
    } catch {
        return $false
    }
}

function Test-PortListening {
    param([int]$Port)
    return [bool](Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
}

function Wait-HttpReady {
    param([string]$Name, [string]$Url)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-HttpReady -Url $Url) {
            Write-Host "[OK] $Name responde en $Url" -ForegroundColor Green
            return $true
        }
        Start-Sleep -Milliseconds 500
    }
    Write-Host "[ERROR] $Name did not respond at $Url within $TimeoutSeconds seconds" -ForegroundColor Red
    return $false
}

function Save-Manifest {
    param([object[]]$Services)
    $manifest = [ordered]@{
        project = $WorkDir
        startedAt = (Get-Date).ToUniversalTime().ToString('o')
        services = @($Services)
    }
    $manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $ManifestPath -Encoding UTF8
}

$freellmpoolCommand = Get-Command $Freellmpool -ErrorAction SilentlyContinue
if (-not $freellmpoolCommand) {
    throw "Freellmpool was not found in the global runtime on E: $Freellmpool"
}

if (Test-Path $ManifestPath) {
    & (Join-Path $WorkDir 'stop-all.ps1') -Quiet
}

if (Test-PortListening -Port $GatewayPort) {
    throw "Port $GatewayPort is already in use. Stop the existing service before continuing."
}
if (Test-PortListening -Port $ApiPort) {
    throw "Port $ApiPort is already in use. Stop the existing service before continuing."
}

$services = @()

Write-Host '[...] Starting Freellmpool...' -ForegroundColor Cyan
$gatewayOut = Join-Path $LogDir 'freellmpool.out.log'
$gatewayErr = Join-Path $LogDir 'freellmpool.err.log'
$gateway = Start-Process -FilePath $freellmpoolCommand.Source `
    -ArgumentList @('proxy', '--host', '127.0.0.1', '--port', "$GatewayPort") `
    -WorkingDirectory $WorkDir -RedirectStandardOutput $gatewayOut `
    -RedirectStandardError $gatewayErr -WindowStyle Hidden -PassThru
$services += [ordered]@{ name = 'freellmpool'; launcherPid = $gateway.Id; listenerPid = $null; port = $GatewayPort }
Save-Manifest -Services $services

if (-not (Wait-HttpReady -Name 'Freellmpool' -Url "http://127.0.0.1:$GatewayPort/v1/models")) {
    Save-Manifest -Services $services
    throw "The gateway did not start. Check $gatewayErr"
}

Write-Host '[...] Starting FastAPI...' -ForegroundColor Cyan
$apiOut = Join-Path $LogDir 'fastapi.out.log'
$apiErr = Join-Path $LogDir 'fastapi.err.log'
$api = Start-Process -FilePath $Python `
    -ArgumentList @('-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', "$ApiPort") `
    -WorkingDirectory $WorkDir -RedirectStandardOutput $apiOut `
    -RedirectStandardError $apiErr -WindowStyle Hidden -PassThru
$services += [ordered]@{ name = 'fastapi'; launcherPid = $api.Id; listenerPid = $null; port = $ApiPort }
Save-Manifest -Services $services

if (-not (Wait-HttpReady -Name 'FastAPI' -Url "http://127.0.0.1:$ApiPort/")) {
    Save-Manifest -Services $services
    & (Join-Path $WorkDir 'stop-all.ps1') -Quiet
    throw "FastAPI did not start. Check $apiErr"
}

foreach ($service in $services) {
    $listener = Get-NetTCPConnection -State Listen -LocalPort $service.port -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($listener) {
        $service.listenerPid = [int]$listener.OwningProcess
    }
    Save-Manifest -Services $services
}

Save-Manifest -Services $services
Write-Host ''
Write-Host 'System started successfully:' -ForegroundColor Green
Write-Host "  - Freellmpool: http://127.0.0.1:$GatewayPort/v1"
Write-Host "  - FastAPI:     http://127.0.0.1:$ApiPort"
Write-Host "  - Manifiesto:  $ManifestPath"
Write-Host 'To stop it: .\stop-all.ps1' -ForegroundColor Cyan
