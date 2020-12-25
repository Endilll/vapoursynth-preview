# pylint: skip-file

import vapoursynth as vs
core = vs.core

# clip0 = core.dgdecodenv.DGSource(r'Pop Team Epic OP.dgi')
clip0 = core.ffms2.Source(r'Pop Team Epic OP.mkv')
clip0 = core.text.FrameNum(clip0)
clip0.set_output(0)

clip0.resize.Bicubic(format=vs.YUV420P10).set_output(1)

clip1 = core.ffms2.Source(r'Cocoro Palette.mp4')
# clip1 = core.ffms2.Source(r'Cross Ange Tenshi to Ryuu no Rondo 01.m2ts')
clip1.set_output(10)

alpha = core.std.BlankClip(width=1280, height=720, length=2232, fpsnum=24000, fpsden=1001, format=vs.GRAY16, color=(32768))
# alpha.set_output(1)

clip0 = core.resize.Point(clip0, format=vs.YUV420P16)
# clip0.set_output(3)
# clip0.set_output(2, alpha)
# clip0 = core.ffms2.Source(r'Pop Team Epic OP.mkv')
# clip1 = core.std.BlankClip(width=848, height=480, color=[77, 255, 90], format=vs.YUV420P8, fpsnum=1000, fpsden=3)
# print('exiting script.vpy...')

# clip1 = core.raws.Source(r'YUV444P8.y4m')
# clip1.set_output(20)

core.std.BlankClip(width=1920, height=1080, length=24, fpsnum=24000, fpsden=1001, format=vs.YUV444P10, color=(40, 0, 0)).set_output(30)

# core.std.BlankClip(width=1920, height=1080, length=24, fpsnum=24000, fpsden=1001, format=vs.GRAY8, color=(0x40)).set_output(31)

core.std.BlankClip( format=vs.YUV444PS, color=(1, 0, -1.5)).set_output(31)
core.std.BlankClip( format=vs.YUV444PS, color=(1, 0, -1)).set_output(32)
core.std.BlankClip( format=vs.YUV444PS, color=(1, 0, -0.5)).set_output(33)
core.std.BlankClip( format=vs.YUV444PS, color=(1, 0, 0)).set_output(34)
core.std.BlankClip( format=vs.YUV444PS, color=(1, 0, 0.5)).set_output(35)
core.std.BlankClip( format=vs.YUV444PS, color=(1, 0, 1)).set_output(36)
core.std.BlankClip( format=vs.YUV444PS, color=(1, 0, 1.5)).set_output(37)

# core.std.BlankClip( format=vs.RGB24, color=(128, 0, 0)).resize.Bicubic(format=vs.COMPATYUY2, matrix='709', matrix_in_s='709').set_output(38)


# clip1 = core.raws.Source(r'YUV444P8 black.y4m')
# clip1.set_output(31)
core.std.LoadPlugin(r'c:\Program Files\VapourSynth\plugins64\BestAudioSource.dll')
audio = core.bas.Source(r'Cocoro Palette.mp4', 1)
audio.set_output(20)
