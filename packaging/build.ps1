param([string]$Version = "1.0.0")

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "== Dependencias =="
& ".venv\Scripts\python" -m pip install -e ".[dev]"

Write-Host "== PyInstaller =="
& ".venv\Scripts\python" -m PyInstaller --noconfirm --clean (Join-Path $PSScriptRoot "iaula.spec") `
    --distpath (Join-Path $root "build\dist") --workpath (Join-Path $root "build\work")

Write-Host "== Clave incluida para el Asistente =="
$dist = Join-Path $root "build\dist\IAulaVirtual"
$keyFile = Join-Path $root ".build\author_key.txt"
if (Test-Path $keyFile) {
    Copy-Item $keyFile (Join-Path $dist "bundled_key.txt") -Force
    Write-Host "  clave incluida"
} else {
    Write-Host "  AVISO: sin .build\author_key.txt -> el Asistente pedira una API key propia"
    "" | Set-Content -Encoding UTF8 (Join-Path $dist "bundled_key.txt")
}

Write-Host "== Instalador (Inno Setup) =="
$iscc = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $iscc)) { $iscc = "C:\Program Files\Inno Setup 6\ISCC.exe" }
if (-not (Test-Path $iscc)) { $iscc = Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe" }
if (-not (Test-Path $iscc)) { throw "No encuentro ISCC.exe (Inno Setup). Instalalo con: winget install JRSoftware.InnoSetup" }
& $iscc "/DMyAppVersion=$Version" (Join-Path $PSScriptRoot "iaula.iss")

Write-Host ""
Write-Host "LISTO: packaging\Output\IAulaVirtual-Setup-$Version.exe"
