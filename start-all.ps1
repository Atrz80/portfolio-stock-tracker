# start-all.ps1 - Inicia Freellmpool y FastAPI, y espera a que estén healthy.
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
$LocalPython = Join-Path $WorkDir '.venv\Scripts\python.exe'
$GlobalHome = if ($env:AI_WORKSTATION_HOME) { $env:AI_WORKSTATION_HOME } else { 'E:\Proyectos\ai-workstation' }
$GlobalPython = Join-Path $GlobalHome '.venv\Scripts\python.exe'
$Python = if (Test-Path -LiteralPath $LocalPython) {
    $LocalPython
} elseif (Test-Path -LiteralPath $GlobalPython) {
    $GlobalPython
} else {
    (Get-Command python -ErrorAction Stop).Source
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
    Write-Host "[ERROR] $Name no respondió en $Url tras $TimeoutSeconds segundos" -ForegroundColor Red
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

if (-not (Test-Path $Python) -and -not (Get-Command $Python -ErrorAction SilentlyContinue)) {
    throw "No se encontró Python. Crea .venv, instala el entorno global o usa Python del sistema."
}

if (Test-Path $ManifestPath) {
    & (Join-Path $WorkDir 'stop-all.ps1') -Quiet
}

if (Test-PortListening -Port $GatewayPort) {
    throw "El puerto $GatewayPort ya está ocupado. Detén el servicio existente antes de continuar."
}
if (Test-PortListening -Port $ApiPort) {
    throw "El puerto $ApiPort ya está ocupado. Detén el servicio existente antes de continuar."
}

$freellmpoolCommand = Get-Command 'freellmpool' -ErrorAction SilentlyContinue
if (-not $freellmpoolCommand) {
    throw "No se encontró el comando 'freellmpool' en PATH."
}

$services = @()

Write-Host '[...] Iniciando Freellmpool...' -ForegroundColor Cyan
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
    throw "El gateway no inició. Revisa $gatewayErr"
}

Write-Host '[...] Iniciando FastAPI...' -ForegroundColor Cyan
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
    throw "FastAPI no inició. Revisa $apiErr"
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
Write-Host 'Sistema iniciado correctamente:' -ForegroundColor Green
Write-Host "  - Freellmpool: http://127.0.0.1:$GatewayPort/v1"
Write-Host "  - FastAPI:     http://127.0.0.1:$ApiPort"
Write-Host "  - Manifiesto:  $ManifestPath"
Write-Host 'Para detenerlo: .\stop-all.ps1' -ForegroundColor Cyan
