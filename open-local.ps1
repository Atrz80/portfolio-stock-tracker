[CmdletBinding()]
param(
    [int]$GatewayPort = 8080,
    [int]$ApiPort = 8000,
    [int]$TimeoutSeconds = 180
)

$ErrorActionPreference = 'Stop'
$WorkDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$DashboardUrl = "http://127.0.0.1:$ApiPort/dashboard"
$ManifestPath = Join-Path $WorkDir '.services.json'
$PreviousStartedAt = $null
if (Test-Path -LiteralPath $ManifestPath) {
    $previousManifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
    $previousProject = [IO.Path]::GetFullPath([string]$previousManifest.project).TrimEnd('\')
    if (-not [string]::Equals($previousProject, $WorkDir.TrimEnd('\'), [StringComparison]::OrdinalIgnoreCase)) {
        throw 'The existing service manifest belongs to a different project folder.'
    }
    $PreviousStartedAt = $previousManifest.startedAt
}
$BrowserCandidates = @(
    (Join-Path $env:ProgramFiles 'Google\Chrome\Application\chrome.exe'),
    (Join-Path ${env:ProgramFiles(x86)} 'Google\Chrome\Application\chrome.exe'),
    (Join-Path $env:LOCALAPPDATA 'Google\Chrome\Application\chrome.exe'),
    (Join-Path $env:ProgramFiles 'Microsoft\Edge\Application\msedge.exe'),
    (Join-Path ${env:ProgramFiles(x86)} 'Microsoft\Edge\Application\msedge.exe')
) | Where-Object { $_ -and (Test-Path -LiteralPath $_) }

if (-not $BrowserCandidates) {
    throw 'Google Chrome or Microsoft Edge could not be found to open the dashboard.'
}

$BrowserPath = $BrowserCandidates | Select-Object -First 1
$ProfilePath = Join-Path $env:TEMP "portfolio-stock-tracker-$PID-$([guid]::NewGuid().ToString('N'))"
$BrowserProcess = $null
$ServicesStarted = $false
$CancelRequested = $false
$CancelHandler = [ConsoleCancelEventHandler]{
    param($Sender, $EventArgs)
    $EventArgs.Cancel = $true
    $script:CancelRequested = $true
}

try {
    Write-Host 'Starting local services...' -ForegroundColor Cyan
    try {
        & (Join-Path $WorkDir 'start-all.ps1') -GatewayPort $GatewayPort -ApiPort $ApiPort -TimeoutSeconds $TimeoutSeconds
    } catch {
        if (Test-Path -LiteralPath $ManifestPath) {
            try {
                $currentManifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
                $currentProject = [IO.Path]::GetFullPath([string]$currentManifest.project).TrimEnd('\')
                if (-not [string]::Equals($currentProject, $WorkDir.TrimEnd('\'), [StringComparison]::OrdinalIgnoreCase)) {
                    throw 'The updated service manifest belongs to a different project folder.'
                }
                $currentStartedAt = $currentManifest.startedAt
                $ServicesStarted = $currentStartedAt -and $currentStartedAt -ne $PreviousStartedAt
            } catch {
                Write-Warning "Could not verify ownership of services after startup failed: $($_.Exception.Message)"
                $ServicesStarted = $false
            }
        }
        throw
    }

    $currentManifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
    if (-not $currentManifest.startedAt -or $currentManifest.startedAt -eq $PreviousStartedAt) {
        throw 'Could not confirm that the launcher started this project''s services.'
    }
    $ServicesStarted = $true

    New-Item -ItemType Directory -Path $ProfilePath -Force | Out-Null
    Write-Host ''
    Write-Host "Abriendo $DashboardUrl" -ForegroundColor Green
    Write-Host 'Close the browser window or press Ctrl+C to stop the application.' -ForegroundColor Cyan
    [Console]::add_CancelKeyPress($CancelHandler)

    $BrowserArguments = @(
        "--app=$DashboardUrl",
        "--user-data-dir=`"$ProfilePath`"",
        '--no-first-run',
        '--disable-background-mode',
        '--disable-extensions'
    )
    $BrowserProcess = Start-Process -FilePath $BrowserPath -ArgumentList $BrowserArguments -PassThru

    while (-not $BrowserProcess.HasExited -and -not $CancelRequested) {
        [void]$BrowserProcess.WaitForExit(500)
    }

    if ($CancelRequested -and -not $BrowserProcess.HasExited) {
        [void]$BrowserProcess.CloseMainWindow()
        if (-not $BrowserProcess.WaitForExit(5000)) {
            Stop-Process -Id $BrowserProcess.Id -Force -ErrorAction Stop
        }
    }
} finally {
    [Console]::remove_CancelKeyPress($CancelHandler)

    try {
        if ($ServicesStarted) {
            Write-Host ''
            Write-Host 'Stopping local services...' -ForegroundColor Cyan
            & (Join-Path $WorkDir 'stop-all.ps1')
        }
    } finally {
        if (Test-Path -LiteralPath $ProfilePath) {
            try {
                Remove-Item -LiteralPath $ProfilePath -Recurse -Force -ErrorAction Stop
            } catch {
                Write-Warning "Could not clean up the temporary browser profile: $($_.Exception.Message)"
            }
        }
    }
}
