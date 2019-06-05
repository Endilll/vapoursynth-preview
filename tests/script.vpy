# pylint: skip-file
import vapoursynth as vs
# import insaneAA
core = vs.core

# clip0 = core.dgdecodenv.DGSource(r'Pop Team Epic OP.dgi')
# clip0 = core.ffms2.Source(r'Pop Team Epic OP.mkv')
# clip0 = core.lsmas.LWLibavSource(r'Pop Team Epic OP.mkv')
clip0 = core.lsmas.LWLibavSource(r'Pop Team Epic OP.mkv')
# print(clip0.get_frame(0).props)
# alpha = core.std.ShufflePlanes(clip0, 0, vs.GRAY)
clip0 = clip0.text.FrameNum()  # type: ignore
clip0.set_output(0)

# clip1 = core.ffms2.Source(r'Cocoro Palette.mp4')
clip1 = core.lsmas.LWLibavSource(r'Cocoro Palette.mp4')
# clip1 = core.ffms2.Source(r'Cross Ange Tenshi to Ryuu no Rondo 01.m2ts')
# clip1.set_output(10)

clip2 = core.imwrif.Read(r'i.jpg')
# clip2.set_output(1)


# clip0 = core.ffms2.Source(r'Pop Team Epic OP.mkv')
# clip1 = core.std.BlankClip(width=848, height=480, color=[77, 255, 90], format=vs.YUV420P8, fpsnum=1000, fpsden=3)
# print('exiting script.vpy...')

# def rescale(clip):
#     luma = core.std.ShufflePlanes(clip, 0, vs.GRAY)
#     desc = insaneAA.revert_upscale(luma, descale_strength=0.3, kernel='bicubic', descale_height=540)
#     rescale = insaneAA.rescale(desc, fasterAA=False, eedi3Mode='opencl', eedi3Device=0, nnedi3Mode='opencl', nnedi3Device=0, dx=1280, dy=720, nsize=6)
#     return rescale

# def apply_mask(clip, aa_luma):
#     luma = core.std.ShufflePlanes(clip, 0, vs.GRAY)
#     linemask = core.std.Sobel(luma).std.Expr('x 2 *').std.Maximum()
#     return core.std.MaskedMerge(luma, aa_luma, linemask)

# episode = clip0

# aa_luma = rescale(episode)
# aa_clip = apply_mask(episode, aa_luma)

# clip1   = core.std.ShufflePlanes([aa_clip, episode], [0,1,2], episode.format.color_family)

# insaneaa = insaneAA.insaneAA(episode, eedi3Mode='opencl', nnedi3Mode='opencl', eedi3Device=0, nnedi3Device=0, descale_strength=0.3, kernel='bicubic', descale_height=540, nsize=6)
# mrgc = insaneaa.std.Trim(0, 683)+episode.std.Trim(684, 698)+insaneaa.std.Trim(699, 2207)

# clip = core.ffms2.Source(r'Pop Team Epic OP.mkv')
clip = core.lsmas.LWLibavSource(r'Pop Team Epic OP.mkv')
# clip = clip.std.SetFrameProp('_Matrix', intval=1)
# print(clip.get_frame(0).props)

clips = []

# clips.append(core.resize.Bicubic(clip=clip, format=vs.GRAY8))     # 0
# clips.append(core.resize.Bicubic(clip=clip, format=vs.GRAY16))    # 1
# clips.append(core.resize.Bicubic(clip=clip, format=vs.GRAYH))     # 2
# clips.append(core.resize.Bicubic(clip=clip, format=vs.GRAYS))     # 3

# clips.append(core.resize.Bicubic(clip=clip, format=vs.YUV420P8))  # 4
# clips.append(core.resize.Bicubic(clip=clip, format=vs.YUV422P8))  # 5
# clips.append(core.resize.Bicubic(clip=clip, format=vs.YUV444P8))  # 6
# clips.append(core.resize.Bicubic(clip=clip, format=vs.YUV410P8))  # 7
# clips.append(core.resize.Bicubic(clip=clip, format=vs.YUV411P8))  # 8
# clips.append(core.resize.Bicubic(clip=clip, format=vs.YUV440P8))  # 9

# clips.append(core.resize.Bicubic(clip=clip, matrix=1, format=vs.YUV420P9))  # 10
# clips.append(core.resize.Bicubic(clip=clip, matrix=1, format=vs.YUV422P9))  # 11
# clips.append(core.resize.Bicubic(clip=clip, matrix=1, format=vs.YUV444P9))  # 12

# clips.append(core.resize.Bicubic(clip=clip, matrix=1, format=vs.YUV420P10))  # 13
# clips.append(core.resize.Bicubic(clip=clip, matrix=1, format=vs.YUV422P10))  # 14
# clips.append(core.resize.Bicubic(clip=clip, matrix=1, format=vs.YUV444P10))  # 15

# clips.append(core.resize.Bicubic(clip=clip, matrix=1, format=vs.YUV420P12))  # 16
# clips.append(core.resize.Bicubic(clip=clip, matrix=1, format=vs.YUV422P12))  # 17
# clips.append(core.resize.Bicubic(clip=clip, matrix=1, format=vs.YUV444P12))  # 18

# clips.append(core.resize.Bicubic(clip=clip, matrix=1, format=vs.YUV420P14))  # 19
# clips.append(core.resize.Bicubic(clip=clip, matrix=1, format=vs.YUV422P14))  # 20
# clips.append(core.resize.Bicubic(clip=clip, matrix=1, format=vs.YUV444P14))  # 21

# clips.append(core.resize.Bicubic(clip=clip, matrix=1, format=vs.YUV420P16))  # 22
# clips.append(core.resize.Bicubic(clip=clip, matrix=1, format=vs.YUV422P16))  # 23
# clips.append(core.resize.Bicubic(clip=clip, matrix=1, format=vs.YUV444P16))  # 24

# clips.append(core.resize.Bicubic(clip=clip, matrix=1, format=vs.YUV444PH))  # 25
# clips.append(core.resize.Bicubic(clip=clip, matrix=1, format=vs.YUV444PS))  # 26

# clips.append(core.resize.Bicubic(clip=clip, format=vs.RGB24))  # 27
# clips.append(core.resize.Bicubic(clip=clip, format=vs.RGB27))  # 28
# clips.append(core.resize.Bicubic(clip=clip, format=vs.RGB30))  # 29
# clips.append(core.resize.Bicubic(clip=clip, format=vs.RGB48))  # 30

# clips.append(core.resize.Bicubic(clip=clip, format=vs.RGBH))  # 31
# clips.append(core.resize.Bicubic(clip=clip, format=vs.RGBS))  # 32

# clips.append(core.resize.Bicubic(clip=clip, format=vs.COMPATBGR32))          # 33
# clips.append(core.resize.Bicubic(clip=clip, matrix=1, format=vs.COMPATYUY2))  # 34

for i in range(len(clips)):
    clips[i].set_output(i)
