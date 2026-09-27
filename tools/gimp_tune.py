# GIMP 3 のバッチ (python-fu-eval) で実行する、ゲーム素材の微調整スクリプト。
#   茶人 : 彩度を少し落とし、暗部を締め、左右と下を闇に溶かして縮小
#   背景 : 暗く沈め、彩度を落とし、軽くぼかして周辺減光
#   和菓子: 余白を切り落として縮小
import os, traceback
import gi
gi.require_version('Gimp', '3.0')
gi.require_version('Gegl', '0.4')
from gi.repository import Gimp, Gio, Gegl

SRC = os.environ['TUNE_SRC']
DST = os.environ['TUNE_DST']
LOG = open(os.path.join(SRC, 'gimp_tune.log'), 'w', encoding='utf-8')
def log(*a):
    LOG.write(' '.join(str(x) for x in a) + '\n'); LOG.flush()

def load(name):
    img = Gimp.file_load(Gimp.RunMode.NONINTERACTIVE, Gio.File.new_for_path(os.path.join(SRC, name)))
    return img, img.get_layers()[0]

def save(img, name):
    layer = img.merge_visible_layers(Gimp.MergeType.CLIP_TO_IMAGE)
    Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, img, Gio.File.new_for_path(os.path.join(DST, name)), None)
    img.delete()
    log('saved', name)

def gegl(layer, op, **props):
    f = Gimp.DrawableFilter.new(layer, op, op)
    cfg = f.get_config()
    for k, v in props.items():
        cfg.set_property(k.replace('_', '-'), v)
    f.update()
    layer.merge_filter(f)

def fade(mask, x1, y1, x2, y2):
    # (x1,y1) で透明、(x2,y2) で不透明になる帯を、マスクに乗算で重ねる
    mask.edit_gradient_fill(Gimp.GradientType.LINEAR, 0, False, 1, 0, True, x1, y1, x2, y2)

def portrait(name):
    img, layer = load(name + '.png')
    w, h = img.get_width(), img.get_height()
    layer.hue_saturation(Gimp.HueRange.ALL, 0, 0, -18, 0)
    for hue in (Gimp.HueRange.CYAN, Gimp.HueRange.BLUE):                 # 切り抜きに残った背景色を抜く
        layer.hue_saturation(hue, 0, 0, -100, 0)
    layer.curves_spline(Gimp.HistogramChannel.VALUE, [0, 0, .25, .2, .6, .58, 1, .96])
    layer.color_balance(Gimp.TransferMode.MIDTONES, True, 4, 0, -6)      # ほんのり行灯色に寄せる
    gegl(layer, 'gegl:unsharp-mask', std_dev=1.2, scale=.35)

    mask = layer.create_mask(Gimp.AddMaskType.ALPHA_TRANSFER)
    layer.add_mask(mask)
    Gimp.context_set_foreground(Gegl.Color.new('black'))
    Gimp.context_set_background(Gegl.Color.new('white'))
    Gimp.context_set_gradient_fg_bg_rgb()
    Gimp.context_set_paint_mode(Gimp.LayerMode.MULTIPLY)
    fade(mask, 0, h, 0, h * .8)             # 下
    fade(mask, 0, 0, w * .17, 0)            # 左
    fade(mask, w, 0, w * .83, 0)            # 右
    Gimp.context_set_paint_mode(Gimp.LayerMode.NORMAL)
    layer.remove_mask(Gimp.MaskApplyMode.APPLY)

    img.scale(w // 2, h // 2)
    save(img, f'tyajin_{name}.webp')

def background(name, out, w2, h2):
    img, layer = load(name + '.png')
    layer.hue_saturation(Gimp.HueRange.ALL, 0, 0, -35, 0)
    layer.curves_spline(Gimp.HistogramChannel.VALUE, [0, 0, .5, .27, 1, .6])
    gegl(layer, 'gegl:gaussian-blur', std_dev_x=3.0, std_dev_y=3.0)
    gegl(layer, 'gegl:vignette', radius=1.7, softness=1.0, gamma=1.0, proportion=.0)
    img.scale(w2, h2)
    save(img, out)

def sweet():
    # 背景除去では暗い皿まで消えてしまうので、元絵から皿ごと楕円で切り抜く
    img, layer = load('wagashi_raw.png')
    layer.add_alpha()
    layer.hue_saturation(Gimp.HueRange.ALL, 0, 0, -10, 0)
    Gimp.context_set_feather(True)
    Gimp.context_set_feather_radius(7, 7)
    img.select_ellipse(Gimp.ChannelOps.REPLACE, 100, 254, 576, 348)
    Gimp.Selection.invert(img)
    layer.edit_clear()
    Gimp.Selection.none(img)
    img.crop(620, 392, 78, 232)
    img.scale(310, 196)
    save(img, 'wagashi.webp')

try:
    for n in ['idle', 'blink', 'watch', 'impressed', 'sigh', 'glare', 'nod', 'drink', 'smile', 'joy']:
        portrait(n)
    background('bg', 'chashitsu.webp', 720, 1280)
    background('bgw', 'chashitsu_wide.webp', 1280, 720)
    sweet()
    log('done')
except Exception:
    log(traceback.format_exc())
LOG.close()
