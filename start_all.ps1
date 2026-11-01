# Alias compatible: el script canónico es start-all.ps1.
& (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Definition) 'start-all.ps1') @args
exit $LASTEXITCODE
