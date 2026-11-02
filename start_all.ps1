# Compatibility alias: the canonical script is start-all.ps1.
& (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Definition) 'start-all.ps1') @args
exit $LASTEXITCODE
