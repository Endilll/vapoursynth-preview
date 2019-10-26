# pylint: skip-file

import vapoursynth as vs
core = vs.core

# clip0 = core.dgdecodenv.DGSource(r'Pop Team Epic OP.dgi')
clip0 = core.ffms2.Source(r'Pop Team Epic OP.mkv')
clip0 = core.text.FrameNum(clip0)
clip0.set_output(0)

clip1 = core.ffms2.Source(r'Cocoro Palette.mp4')
# clip1 = core.ffms2.Source(r'Cross Ange Tenshi to Ryuu no Rondo 01.m2ts')
clip1.set_output(10)

alpha = core.std.BlankClip(width=1280, height=720, length=2232, fpsnum=24000, fpsden=1001, format=vs.GRAY16, color=(32768))
alpha.set_output(1)

clip0 = core.resize.Point(clip0, format=vs.YUV420P16)
clip0.set_output(3)
clip0.set_output(2, alpha)
# clip0 = core.ffms2.Source(r'Pop Team Epic OP.mkv')
# clip1 = core.std.BlankClip(width=848, height=480, color=[77, 255, 90], format=vs.YUV420P8, fpsnum=1000, fpsden=3)
# print('exiting script.vpy...')
