# Capturas 2K para el cliente, cuadros del video 2K y armado del mp4. Se puede volver a lanzar: lo ya hecho no se repite.
$b = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
$p = "C:\Users\angel\Proyectos\BaseSucre3D"
$py = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
"capturas: " + (Get-Date -Format HH:mm)
& $b --background "$p\BaseSucre.blend" --python "$p\scripts\capturas_cliente.py" 2>&1 | Select-String -Pattern 'captura|falta|Error|Traceback'
"video: " + (Get-Date -Format HH:mm)
# en tandas de 120 cuadros: si Blender se cae, la siguiente tanda sigue (los cuadros hechos se saltan)
for ($a = 1; $a -le 865; $a += 120) {
    $z = [math]::Min($a + 119, 865)
    & $b --background "$p\BaseSucre.blend" --python "$p\scripts\video_recorrido.py" -- render $a $z 2>&1 | Select-String -Pattern 'Error|Traceback|EXCEPTION'
    "  cuadros $a-$z " + (Get-Date -Format HH:mm)
}
"armando: " + (Get-Date -Format HH:mm)
& $py -I "$p\scripts\armar_video.py" $p
"fin: " + (Get-Date -Format HH:mm)
