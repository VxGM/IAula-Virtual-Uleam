param(
    [string]$Version = "1.2.0",
    [string]$Sign = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "== Dependencias =="
& ".venv\Scripts\python" -m pip install -e ".[dev]"

Write-Host "== PyInstaller =="
& ".venv\Scripts\python" -m PyInstaller --noconfirm --clean (Join-Path $PSScriptRoot "iaula.spec") `
    --distpath (Join-Path $root "build\dist") --workpath (Join-Path $root "build\work")

$dist = Join-Path $root "build\dist\IAulaVirtual"
if (Test-Path (Join-Path $dist "bundled_key.txt")) {
    Remove-Item (Join-Path $dist "bundled_key.txt") -Force
}

function Sign-File([string]$Path) {
    if (-not $Sign) { return }
    $signtool = (Get-Command signtool.exe -ErrorAction SilentlyContinue).Source
    if (-not $signtool) { throw "signtool.exe no esta en PATH (instala Windows SDK)." }
    Write-Host "  firmando $(Split-Path -Leaf $Path)"
    & $signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 /a /f $Sign $Path
    if ($LASTEXITCODE -ne 0) { throw "La firma fallo: $Path" }
}

Write-Host "== Firma (opcional) =="
Sign-File (Join-Path $dist "IAulaVirtual.exe")

Write-Host "== Instalador (Inno Setup) =="
$iscc = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $iscc)) { $iscc = "C:\Program Files\Inno Setup 6\ISCC.exe" }
if (-not (Test-Path $iscc)) { $iscc = Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe" }
if (-not (Test-Path $iscc)) { throw "No encuentro ISCC.exe (Inno Setup). Instalalo con: winget install JRSoftware.InnoSetup" }
& $iscc "/DMyAppVersion=$Version" (Join-Path $PSScriptRoot "iaula.iss")

$setup = Join-Path $PSScriptRoot "Output\IAulaVirtual-Setup-$Version.exe"
Sign-File $setup

Write-Host "== Hashes =="
$lines = @()
foreach ($file in @((Join-Path $dist "IAulaVirtual.exe"), $setup)) {
    if (Test-Path $file) {
        $hash = (Get-FileHash $file -Algorithm SHA256).Hash.ToLower()
        $lines += "$hash  $(Split-Path -Leaf $file)"
    }
}
$sums = Join-Path $PSScriptRoot "Output\SHA256SUMS.txt"
$lines | Set-Content -Encoding ASCII $sums
Write-Host "  $sums"

Write-Host ""
Write-Host "LISTO: $setup"
