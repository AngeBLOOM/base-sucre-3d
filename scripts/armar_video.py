"""Une los cuadros de renders/video en un mp4 2K (H.264, 24 fps) con fundido de entrada y salida y el título.

    python armar_video.py <carpeta del proyecto>
"""
import glob
import os
import subprocess
import sys

import imageio_ffmpeg

RAIZ = sys.argv[1]
cuadros = sorted(glob.glob(os.path.join(RAIZ, "renders", "video", "cuadro_*.png")))
n = len(cuadros)
dur = n / 24.0
ff = imageio_ffmpeg.get_ffmpeg_exe()
fuente = "C\\:/Windows/Fonts/segoeuib.ttf" if os.path.exists(r"C:\Windows\Fonts\segoeuib.ttf") else "C\\:/Windows/Fonts/arialbd.ttf"
fuente2 = "C\\:/Windows/Fonts/segoeui.ttf" if os.path.exists(r"C:\Windows\Fonts\segoeui.ttf") else "C\\:/Windows/Fonts/arial.ttf"
titulo = ("drawtext=fontfile='{f}':text='BASE AÉREA ESCUELA MARISCAL SUCRE':fontcolor=white:fontsize=78:"
          "x=(w-text_w)/2:y=h*0.42:shadowcolor=black@0.6:shadowx=3:shadowy=3:"
          "alpha='if(lt(t,0.6),0,if(lt(t,1.6),(t-0.6),if(lt(t,4.2),1,if(lt(t,5.2),5.2-t,0))))'").format(f=fuente)
sub = ("drawtext=fontfile='{f}':text='Maracay · Venezuela · Recorrido 3D':fontcolor=white:fontsize=40:"
       "x=(w-text_w)/2:y=h*0.42+100:shadowcolor=black@0.6:shadowx=2:shadowy=2:"
       "alpha='if(lt(t,1.0),0,if(lt(t,2.0),(t-1.0),if(lt(t,4.2),1,if(lt(t,5.2),5.2-t,0))))'").format(f=fuente2)
filtro = f"{titulo},{sub},fade=t=in:st=0:d=0.8,fade=t=out:st={max(dur - 1.2, 0):.2f}:d=1.2"
salida = os.path.join(RAIZ, "renders", "Recorrido_Base_Sucre_2K.mp4")
cmd = [ff, "-y", "-framerate", "24", "-i", os.path.join(RAIZ, "renders", "video", "cuadro_%04d.png"),
       "-vf", filtro, "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p",
       "-movflags", "+faststart", salida]
subprocess.run(cmd, check=True)
print("video:", salida, f"{n} cuadros, {dur:.1f} s")
