param([string]$Time = "07:30")

$bat = Join-Path $PSScriptRoot "run-check.bat"
schtasks /Create /F /SC DAILY /ST $Time /TN "IAula-Check" /TR "`"$bat`""
