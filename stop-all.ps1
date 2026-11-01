# stop-all.ps1 - Stops only the services started by start-all.ps1.
[CmdletBinding(SupportsShouldProcess = $true)]
param([switch]$Quiet)

$ErrorActionPreference = 'Stop'
$WorkDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ManifestPath = Join-Path $WorkDir '.services.json'
$GlobalHome = if ($env:AI_WORKSTATION_HOME) { $env:AI_WORKSTATION_HOME } else { 'E:\Proyectos\ai-workstation' }
$RuntimeRoot = Join-Path $GlobalHome 'runtime'
$ExpectedPython = Join-Path $RuntimeRoot 'venv\Scripts\python.exe'
$ExpectedFreellmpool = Join-Path $RuntimeRoot 'venv\Scripts\freellmpool.exe'

if (-not (Test-Path $ManifestPath)) {
    if (-not $Quiet) { Write-Host 'No hay manifiesto de servicios; nada que detener.' }
    exit 0
}

try {
    $manifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
} catch {
    if (-not $Quiet) { Write-Host "Invalid manifest: $($_.Exception.Message)" -ForegroundColor Red }
    exit 1
}

$manifestProject = [IO.Path]::GetFullPath([string]$manifest.project).TrimEnd('\')
if (-not [string]::Equals($manifestProject, $WorkDir.TrimEnd('\'), [StringComparison]::OrdinalIgnoreCase)) {
    if (-not $Quiet) { Write-Host 'The manifest belongs to another folder; no process was stopped.' -ForegroundColor Red }
    exit 1
}

$processSnapshot = @(Get-CimInstance -ClassName Win32_Process)
$processById = @{}
$childrenByParent = @{}
foreach ($process in $processSnapshot) {
    $processById[[int]$process.ProcessId] = $process
    $parentId = [int]$process.ParentProcessId
    if (-not $childrenByParent.ContainsKey($parentId)) {
        $childrenByParent[$parentId] = [System.Collections.Generic.List[int]]::new()
    }
    $childrenByParent[$parentId].Add([int]$process.ProcessId)
}

function Test-ExpectedServiceProcess {
    param(
        [object]$Process,
        [string]$ServiceName,
        [int]$Port
    )

    $commandLine = [string]$Process.CommandLine
    if (-not $commandLine) { return $false }
    $portArgument = "(?i)(--port(?:\s+|=))$Port(?:\s|$)"
    if ($commandLine -notmatch $portArgument) { return $false }

    if ($ServiceName -eq 'fastapi') {
        return $commandLine -match '(?i)-m\s+uvicorn\s+main:app\b'
    }
    if ($ServiceName -eq 'freellmpool') {
        return $commandLine -match '(?i)\bfreellmpool(?:\.exe)?\b.*\bproxy\b'
    }
    return $false
}

$verifiedRoots = [System.Collections.Generic.HashSet[int]]::new()
foreach ($service in @($manifest.services)) {
    $serviceName = [string]$service.name
    $port = [int]$service.port
    $launcherPid = [int]$service.launcherPid
    $listenerPid = if ($null -ne $service.listenerPid) { [int]$service.listenerPid } else { 0 }
    $expectedLauncher = if ($serviceName -eq 'fastapi') { $ExpectedPython } else { $ExpectedFreellmpool }

    if ($processById.ContainsKey($launcherPid)) {
        $launcher = $processById[$launcherPid]
        if (
            [string]::Equals([string]$launcher.ExecutablePath, $expectedLauncher, [StringComparison]::OrdinalIgnoreCase) -and
            (Test-ExpectedServiceProcess -Process $launcher -ServiceName $serviceName -Port $port)
        ) {
            [void]$verifiedRoots.Add($launcherPid)
        } elseif (-not $Quiet) {
            Write-Host "[--] PID $launcherPid does not match the recorded launcher; skipped." -ForegroundColor Yellow
        }
    }

    $listenerOwnsPort = $false
    if ($listenerPid -gt 0) {
        $listenerOwnsPort = [bool](
            Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue |
                Where-Object { [int]$_.OwningProcess -eq $listenerPid }
        )
    }
    if ($listenerOwnsPort -and $processById.ContainsKey($listenerPid)) {
        $listener = $processById[$listenerPid]
        if (Test-ExpectedServiceProcess -Process $listener -ServiceName $serviceName -Port $port) {
            [void]$verifiedRoots.Add($listenerPid)
        } elseif (-not $Quiet) {
            Write-Host "[--] PID $listenerPid does not match the service on port $port; skipped." -ForegroundColor Yellow
        }
    }
}

$stopOrder = [System.Collections.Generic.List[int]]::new()
$visited = [System.Collections.Generic.HashSet[int]]::new()
function Add-ProcessTreeToStopOrder {
    param([int]$ProcessId)

    if (-not $visited.Add($ProcessId)) { return }
    if ($childrenByParent.ContainsKey($ProcessId)) {
        foreach ($childId in $childrenByParent[$ProcessId]) {
            Add-ProcessTreeToStopOrder -ProcessId $childId
        }
    }
    $stopOrder.Add($ProcessId)
}

foreach ($rootPid in $verifiedRoots) {
    Add-ProcessTreeToStopOrder -ProcessId $rootPid
}

$stopFailed = $false
foreach ($processId in $stopOrder) {
    try {
        if ($PSCmdlet.ShouldProcess("PID $processId", 'Stop process')) {
            Stop-Process -Id $processId -Force -ErrorAction Stop
            if (-not $Quiet) { Write-Host "[OK] Detenido PID $processId" -ForegroundColor Green }
        }
    } catch {
        if (Get-Process -Id $processId -ErrorAction SilentlyContinue) {
            $stopFailed = $true
            Write-Warning "Could not stop PID $processId`: $($_.Exception.Message)"
        }
    }
}

if ($stopFailed) {
    throw 'Some registered processes could not be stopped; the manifest is kept for another attempt.'
}

if ($PSCmdlet.ShouldProcess($ManifestPath, 'Remove service manifest')) {
    Remove-Item -LiteralPath $ManifestPath -Force
    if (-not $Quiet) { Write-Host 'All project services are stopped.' -ForegroundColor Green }
} elseif (-not $Quiet) {
    Write-Host 'Preview complete: no process was stopped and the manifest was kept.' -ForegroundColor Cyan
}
