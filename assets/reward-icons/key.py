import sys
from PIL import Image, ImageDraw, ImageFilter
src, dst = sys.argv[1], sys.argv[2]
im = Image.open(src).convert("RGB").resize((512,512), Image.LANCZOS)
w,h = im.size
SENT=(255,0,255)
seeds=[(0,0),(w-1,0),(0,h-1),(w-1,h-1),(w//2,0),(w//2,h-1),(0,h//2),(w-1,h//2),(4,4),(w-5,4),(4,h-5),(w-5,h-5),(w//2,6),(w//2,h-7),(6,h//2),(w-7,h//2)]
for s in seeds:
    try: ImageDraw.floodfill(im, s, SENT, thresh=140)
    except Exception: pass
rgba=im.convert("RGBA")
datum=list(im.getdata())
mask=Image.frombytes("L",(w,h),bytes(0 if p==SENT else 255 for p in datum))
mask=mask.filter(ImageFilter.MinFilter(5))   # erode ~2px -> kill light fringe
rgba.putalpha(mask)
bbox=rgba.getchannel("A").getbbox()
if bbox: rgba=rgba.crop(bbox)
ww,hh=rgba.size; s2=int(max(ww,hh)*1.12)
cv=Image.new("RGBA",(s2,s2),(0,0,0,0)); cv.paste(rgba,((s2-ww)//2,(s2-hh)//2),rgba)
cv=cv.resize((512,512),Image.LANCZOS); cv.save(dst)
