# stop-all.ps1 - Detiene únicamente los servicios iniciados por start-all.ps1.
[CmdletBinding()]
param([switch]$Quiet)

$ErrorActionPreference = 'Stop'
$WorkDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ManifestPath = Join-Path $WorkDir '.services.json'

if (-not (Test-Path $ManifestPath)) {
    if (-not $Quiet) { Write-Host 'No hay manifiesto de servicios; nada que detener.' }
    exit 0
}

try {
    $manifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
} catch {
    if (-not $Quiet) { Write-Host "Manifiesto inválido: $($_.Exception.Message)" -ForegroundColor Red }
    exit 1
}

foreach ($service in @($manifest.services)) {
    $launcherPid = [int]$service.launcherPid
    $listenerPid = if ($null -ne $service.listenerPid) { [int]$service.listenerPid } else { 0 }

    if (Get-Process -Id $launcherPid -ErrorAction SilentlyContinue) {
        & taskkill.exe /PID $launcherPid /T /F *> $null
        if (-not $Quiet) { Write-Host "[OK] Detenido $($service.name) (proceso y descendientes)" -ForegroundColor Green }
    }

    if ($listenerPid -gt 0 -and (Get-Process -Id $listenerPid -ErrorAction SilentlyContinue)) {
        Stop-Process -Id $listenerPid -Force -ErrorAction SilentlyContinue
        if (-not $Quiet) { Write-Host "[OK] Detenido worker de $($service.name) (PID $listenerPid)" -ForegroundColor Green }
    } elseif (-not $Quiet) {
        Write-Host "[--] $($service.name) ya estaba detenido" -ForegroundColor Yellow
    }
}

Remove-Item -LiteralPath $ManifestPath -Force -ErrorAction SilentlyContinue
if (-not $Quiet) { Write-Host 'Todos los servicios del proyecto están detenidos.' -ForegroundColor Green }
