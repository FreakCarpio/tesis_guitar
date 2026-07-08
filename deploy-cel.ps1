# deploy-cel.ps1 — compila e instala FretMind en el celular sin abrir Android Studio.
# Uso:  .\deploy-cel.ps1              (usa el cel ya conectado por USB o Wi-Fi)
#       .\deploy-cel.ps1 192.168.1.50:5555   (conecta primero a esa IP de Wireless debugging)

param([string]$Ip)

$adb = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"
$app = Join-Path $PSScriptRoot "android app"
$pkg = "com.example.prueba"

if ($Ip) {
    & $adb connect $Ip
}

$devices = (& $adb devices) | Select-String "device$"
if (-not $devices) {
    Write-Host "No hay ningun celular conectado." -ForegroundColor Red
    Write-Host "Conecta por USB, o activa 'Depuracion inalambrica' en el cel y corre:"
    Write-Host "  .\deploy-cel.ps1 <IP:puerto que muestra el cel>"
    exit 1
}

Push-Location $app
try {
    & .\gradlew.bat installDebug
    if ($LASTEXITCODE -ne 0) { Write-Host "Fallo el build/instalacion." -ForegroundColor Red; exit 1 }
} finally {
    Pop-Location
}

# Relanza la app para que abra con la version nueva. El mismo cel puede
# aparecer dos veces (mDNS + IP:puerto): se apunta al primer serial con -s
# porque adb rechaza comandos shell ambiguos con varios dispositivos.
$serial = ((& $adb devices) | Select-String "device$" | Select-Object -First 1).Line.Split()[0]
& $adb -s $serial shell am force-stop $pkg
& $adb -s $serial shell monkey -p $pkg -c android.intent.category.LAUNCHER 1 | Out-Null
Write-Host "Listo: FretMind actualizado y abierto en el cel." -ForegroundColor Green
