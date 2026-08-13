#!/usr/bin/env python3
"""Render the offer-drafter Geometry Board scenes as local SVG files."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

W, H = 1200, 675
BLACK, GRAY, GUIDE, LIGHT, FILL, BLUE = "#111111", "#666666", "#B8B8B8", "#E8E8E8", "#F5F5F5", "#2F6BFF"
FONT = "-apple-system,BlinkMacSystemFont,'PingFang SC','Noto Sans CJK SC',sans-serif"


def txt(x, y, value, size=16, fill=BLACK, anchor="middle", weight=400):
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="{FONT}" font-size="{size}px" font-weight="{weight}" fill="{fill}">{html.escape(value)}</text>'


def line(x1, y1, x2, y2, color=BLACK, width=1.5, arrow=False, dashed=False):
    marker = ' marker-end="url(#arrow)"' if arrow else ""
    dash = ' stroke-dasharray="5 7"' if dashed else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}"{dash}{marker}/>'


def path(d, color=BLACK, width=1.5, arrow=False, dashed=False):
    marker = ' marker-end="url(#arrow)"' if arrow else ""
    dash = ' stroke-dasharray="5 7"' if dashed else ""
    return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}"{dash}{marker}/>'


def box(x, y, w, h, fill="#FFFFFF", stroke=BLACK, width=1.5):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>'


def heading(scene):
    intent = scene["intent"]
    return "".join([txt(96, 78, intent["core_message"], 32, BLACK, "start", 650), txt(96, 108, intent["subtitle"], 14, GRAY, "start"), line(96, 136, 1104, 136, LIGHT, 1)])


def offer_package(scene):
    body = [heading(scene)]
    cash = [(300, "基础薪资", "周期薪资"), (600, "目标奖金", "基础 × 比例，目标值"), (900, "首年签字费", "仅计入首年")]
    for x, label, detail in cash:
        body.extend([box(x - 118, 210, 236, 74, FILL, "#222222", 1.2), txt(x, 244, label, 17, BLACK, weight=650), txt(x, 268, detail, 12, GRAY), path(f"M {x} 288 C {x} 330 600 320 600 372", BLACK, 1.4, True)])
    body.extend(['<circle cx="600" cy="420" r="60" fill="#2F6BFF"/>', txt(600, 414, "现金", 18, "#FFFFFF", weight=650), txt(600, 440, "首年总包", 18, "#FFFFFF", weight=650)])
    body.extend([box(900, 392, 236, 96, "#FFFFFF", GUIDE, 1.5), txt(1018, 424, "股权", 17, BLACK, weight=650), txt(1018, 448, "按行权安排单列", 12, GRAY), txt(1018, 470, "不折成现金", 12, BLUE), line(720, 458, 890, 458, GUIDE, 1.2, dashed=True), txt(805, 448, "分开", 12, GRAY)])
    body.append(txt(600, 560, "现金按口径相加，股权单列——不把两类混成一个数字", 14, BLACK, weight=600))
    return "".join(body)


def approval_gate(scene):
    body = [heading(scene), '<circle cx="196" cy="360" r="56" fill="#FFFFFF" stroke="#222222" stroke-width="1.5"/>', txt(196, 355, "Offer", 17, BLACK, weight=650), txt(196, 379, "草稿", 17, BLACK, weight=650)]
    gates = [(470, "带宽核对", "区间内 / 带宽外"), (700, "编制 · 薪酬审批", "approved / pending"), (930, "合规复核", "条款 / 措辞")]
    prev = 252
    for x, label, detail in gates:
        body.extend([box(x - 96, 322, 192, 76, FILL, "#222222", 1.2), txt(x, 352, label, 15, BLACK, weight=650), txt(x, 376, detail, 12, GRAY), line(prev, 360, x - 100, 360, BLACK, 1.5, True)])
        prev = x + 96
    body.extend([line(prev, 360, 1058, 360, GUIDE, 1.5, True, dashed=True), box(1058, 326, 84, 68, "#FFFFFF", BLUE, 1.5), txt(1100, 356, "人确认", 14, BLUE, weight=650), txt(1100, 378, "后发送", 12, GRAY)])
    body.append(txt(600, 470, "每一道闸门只标状态，不替人做“能不能发”的决定", 14, GRAY))
    body.extend([txt(470, 452, "↑ 带宽外→需额外审批", 12, BLUE), txt(700, 452, "↑ 非 approved→待确认", 12, BLUE)])
    return "".join(body)


def draft_flow(scene):
    body = [heading(scene)]
    steps = [(190, "脱敏要素", "岗位·职级·薪酬组成"), (450, "校验", "脱敏 · 口径 · 带宽"), (710, "草稿", "薪酬包 · Letter · 提示"), (970, "人工复核", "定薪 · 审批 · 发送")]
    for i, (x, label, detail) in enumerate(steps):
        accent = i == len(steps) - 1
        body.extend([box(x - 104, 320, 208, 84, "#FFFFFF" if not accent else FILL, BLUE if accent else "#222222", 1.5 if accent else 1.3), txt(x, 352, label, 17, BLUE if accent else BLACK, weight=650), txt(x, 378, detail, 12, GRAY)])
        if i:
            body.append(line(steps[i - 1][0] + 104, 362, x - 108, 362, BLACK, 1.5, True))
    body.extend([line(710, 300, 710, 260, GUIDE, 1, dashed=True), txt(710, 244, "只到草稿为止", 13, BLUE, weight=600)])
    body.append(txt(600, 486, "Agent 把要素做成可复核草稿，发送与定薪留给人", 14, GRAY))
    return "".join(body)


def human_boundary(scene):
    body = [heading(scene), '<rect x="112" y="200" width="452" height="322" fill="#F5F5F5"/>', '<rect x="704" y="200" width="384" height="322" fill="#FFFFFF" stroke="#E8E8E8" stroke-width="1"/>', line(640, 188, 640, 540, GUIDE, 1, dashed=True), txt(338, 232, "Agent", 15, GRAY, weight=650), txt(896, 232, "招聘负责人 · 合规", 15, GRAY, weight=650)]
    body.extend(['<circle cx="260" cy="350" r="56" fill="#FFFFFF" stroke="#222222" stroke-width="1.5"/>', txt(260, 345, "整理", 17, BLACK, weight=650), txt(260, 370, "拟稿", 17, BLACK, weight=650), line(330, 350, 462, 350, BLACK, 1.5, True), box(466, 314, 88, 72, "#FFFFFF", "#222222", 1.5), txt(510, 344, "标记", 16, BLACK, weight=650), txt(510, 367, "待确认", 12, GRAY), line(554, 350, 616, 350, BLACK, 1.5, True), '<circle cx="640" cy="350" r="17" fill="#2F6BFF"/>', txt(640, 416, "发送闸门", 13, BLUE, weight=650), line(664, 350, 756, 350, BLACK, 1.5, True), '<circle cx="870" cy="350" r="72" fill="#FFFFFF" stroke="#222222" stroke-width="1.5"/>', '<circle cx="870" cy="350" r="47" fill="none" stroke="#E8E8E8" stroke-width="1"/>', txt(870, 343, "定薪 · 审批", 15, BLACK, weight=650), txt(870, 369, "确认后发送", 13, GRAY), txt(338, 488, "只交付 offer 草稿", 13, GRAY), txt(896, 488, "承担发送与定薪责任", 13, GRAY)])
    return "".join(body)


def render(scene):
    composition = scene["intent"]["composition"]
    functions = {"converge-flow": offer_package, "gate-flow": approval_gate, "left-right-flow": draft_flow, "section-space": human_boundary}
    body = functions[composition](scene)
    title = html.escape(scene["intent"]["core_message"])
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<title>{title}</title><desc>Geometry Board for Offer 起草.</desc>
<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto" markerUnits="strokeWidth"><path d="M 0 0 L 8 4 L 0 8 z" fill="#111111"/></marker></defs>
<rect width="1200" height="675" fill="#FFFFFF"/>{body}</svg>\n'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scene_dir", type=Path, nargs="?", default=Path(__file__).resolve().parents[1] / "assets" / "scenes")
    parser.add_argument("output_dir", type=Path, nargs="?", default=Path(__file__).resolve().parents[1] / "assets" / "boards")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for scene_path in sorted(args.scene_dir.glob("*.json")):
        scene = json.loads(scene_path.read_text(encoding="utf-8"))
        output = args.output_dir / f"{scene_path.stem}.svg"
        output.write_text(render(scene), encoding="utf-8")
        print(output)


if __name__ == "__main__":
    main()
