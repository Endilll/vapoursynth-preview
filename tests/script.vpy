# pylint: skip-file

import vapoursynth as vs
core = vs.core

# clip0 = core.dgdecodenv.DGSource(r'Pop Team Epic OP.dgi')
clip0 = core.ffms2.Source(r'Pop Team Epic OP.mkv')
clip0.set_output(0)

clip1 = core.ffms2.Source(r'Cocoro Palette.mp4')
# clip1 = core.ffms2.Source(r'Cross Ange Tenshi to Ryuu no Rondo 01.m2ts')
clip1.set_output(10)


# clip0 = core.ffms2.Source(r'Pop Team Epic OP.mkv')
# clip1 = core.std.BlankClip(width=848, height=480, color=[77, 255, 90], format=vs.YUV420P8, fpsnum=1000, fpsden=3)
# print('exiting script.vpy...')
