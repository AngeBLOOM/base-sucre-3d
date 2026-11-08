# Render que no ahoga la laptop: Blender con prioridad baja y 4 hilos, en borrador (por defecto) o final.
#   powershell -File scripts\render.ps1 -Carpeta revision -Tomas "Cam_DIDA:dida,Cam_CAA:caa"
#   powershell -File scripts\render.ps1 -Carpeta cliente_v3 -Tomas "..." -Final
param([string]$Carpeta = "borrador", [string]$Tomas = "", [switch]$Final, [int]$Hilos = 4)
$raiz = Split-Path -Parent $PSScriptRoot
$b = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
$log = Join-Path $raiz "renders\render.log"
$modo = if ($Final) { "final" } else { "borrador" }
$argList = @("--background", (Join-Path $raiz "BaseSucre.blend"), "-t", "$Hilos",
          "--python", (Join-Path $PSScriptRoot "capturas_hoy.py"), "--", $Carpeta, "`"$Tomas`"", $modo)
$p = Start-Process -FilePath $b -ArgumentList $argList -PassThru -NoNewWindow -RedirectStandardOutput $log `
                   -RedirectStandardError (Join-Path $raiz "renders\render_err.log")
Start-Sleep -Milliseconds 500
try { $p.PriorityClass = "BelowNormal" } catch {}
$p.WaitForExit()
Get-Content $log | Select-String "^modo|^captura|^salto|recorte|Error|rror:"
