"""
icon_assets.py - 用 Pillow 动态生成托盘图标，无需外部图片文件
"""

from PIL import Image, ImageDraw

STATUS_COLORS = {
    "connected": "#4CAF50",    # 绿
    "connecting": "#FFC107",   # 黄
    "stopped": "#9E9E9E",      # 灰
    "error": "#F44336",        # 红
}

SIZE = 64


def make_icon(status: str) -> Image.Image:
    color = STATUS_COLORS.get(status, STATUS_COLORS["stopped"])
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    margin = 6
    draw.ellipse(
        [margin, margin, SIZE - margin, SIZE - margin],
        fill=color,
        outline="#ffffff",
        width=3,
    )
    return img
