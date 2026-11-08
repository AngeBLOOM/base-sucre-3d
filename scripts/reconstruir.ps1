# Rehace BaseSucre.blend desde cero en el orden correcto y, con -Capturas <carpeta>, saca las capturas 2K.
#   powershell -File scripts\reconstruir.ps1 [-Capturas cliente_v2]
param([string]$Capturas = "")

# prioridad baja: Blender (hijo de este proceso) la hereda y la laptop sigue usable mientras reconstruye
try { (Get-Process -Id $PID).PriorityClass = "BelowNormal" } catch {}
$raiz = Split-Path -Parent $PSScriptRoot
$b = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
$blend = Join-Path $raiz "BaseSucre.blend"
$log = Join-Path $raiz "renders\reconstruir.log"
"=== $(Get-Date) ===" | Out-File $log -Encoding utf8
$t0 = Get-Date
function Paso($nombre, $argsExtra) {
    $t = Get-Date
    $script = Join-Path $PSScriptRoot "$nombre.py"
    if ($nombre -eq "construir_base") {
        & $b --background --factory-startup --python $script -- $raiz *>> $log
    } else {
        & $b --background $blend --python $script @argsExtra *>> $log
    }
    "{0,-22} {1,5:n0} s" -f $nombre, ((Get-Date) - $t).TotalSeconds | Tee-Object -FilePath $log -Append
}
foreach ($p in "construir_base", "entrada", "entrada_adentro", "dida", "hangares", "g14_hangar3", "dorm_g7",
                "comando_g19", "bomberos", "combustible_azul", "comedor", "comedor_vecinos", "caa_vecinos", "academia",
                "edificios_genericos", "vias", "calidad", "palmas_pasto", "entorno", "acabado", "camino_dida") {
    Paso $p @()
}
Paso "video_recorrido" @("--", "preparar")
"escena lista en {0:n0} min" -f ((Get-Date) - $t0).TotalMinutes | Tee-Object -FilePath $log -Append
if ($Capturas) {
    Paso "capturas_cliente" @("--", $Capturas)
    "capturas listas en {0:n0} min" -f ((Get-Date) - $t0).TotalMinutes | Tee-Object -FilePath $log -Append
}
