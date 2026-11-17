# Firmar el instalador (Authenticode)

Sin firma, Windows SmartScreen muestra una advertencia al ejecutar el instalador
por primera vez. Firmar no elimina el aviso de inmediato (la reputación se gana
con descargas), pero es requisito para que antivirus y SmartScreen confíen en el
binario.

## Qué necesitas

- Un certificado de firma de código **OV** (Organization Validation) o **EV**
  (Extended Validation), en formato `.pfx` con su contraseña.
- Almacenamiento seguro del `.pfx`: nunca debe entrar al repositorio. Guárdalo
  fuera del proyecto, por ejemplo en `%USERPROFILE%\.secrets\`.
- `signtool.exe` (Windows SDK) en el `PATH`.

Alternativas al `.pfx` tradicional:

- **Azure Trusted Signing** (recomendado si ya usas Azure): firma desde la nube
  sin manejar el `.pfx`; sustituye el bloque `Sign-File` por `signtool` con
  `/dlib` y `/dmdf`.
- **Certificado EV en token USB**: requiere el token conectado durante el build.

## Cómo firmar

El build ya acepta el parámetro `-Sign`:

```powershell
powershell -ExecutionPolicy Bypass -File packaging\build.ps1 `
    -Version 1.2.0 `
    -Sign "C:\Users\ASUS\.secrets\iaula-codesign.pfx"
```

Orden de firma:

1. `IAulaVirtual.exe` (antes de empaquetar, para que el instalador lo incluya firmado).
2. `IAulaVirtual-Setup-1.2.0.exe` (después de Inno Setup).

El script usa SHA-256 y timestamp de DigiCert
(`http://timestamp.digicert.com`), así la firma sigue siendo válida cuando
caduca el certificado.

## Verificar

```powershell
signtool verify /pa /v packaging\Output\IAulaVirtual-Setup-1.2.0.exe
Get-AuthenticodeSignature packaging\Output\IAulaVirtual-Setup-1.2.0.exe | Format-List
```

Debe aparecer `Status: Valid` y el nombre del certificado.

## Antes de comprar

- Un certificado OV suele costar menos y ya permite firmar; la reputación de
  SmartScreen se construye con descargas.
- Un certificado EV (token) da reputación inmediata en SmartScreen, pero es más
  caro y complica el build (el token debe estar conectado).
- Si no puedes firmar todavía, publica siempre `SHA256SUMS.txt` y explica el
  aviso en la web (ya está redactado en `SECURITY.md` y en la landing).

## Notas

- Nunca subas el `.pfx` ni su contraseña al repositorio.
- Si usas CI, guarda el `.pfx` como secreto en base64 y descífralo solo durante
  el job de build.
- Firma también las releases antiguas solo si las vuelves a publicar; no cambies
  el binario de una release existente.
