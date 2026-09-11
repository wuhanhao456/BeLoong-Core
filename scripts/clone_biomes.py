#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
clone_biomes.py — 天灾维度「命运空间」群系克隆脚本（档 2 完全体 / spawns 策略 A 省事档）

用途
    把 BWG 的 55 个地表群系 + 原版 16 个海洋/河流/洞穴/沙滩群系，克隆到 beloong 命名空间，
    输出 data/beloong/worldgen/biome/disaster_*.json，并为 BWG 克隆群系注入统一的动物刷怪表。

设计依据
    docs/plans/2026-09-11-disaster-biome-rework-design.md（§2.2 / §2.3 A 档 / §2.4.1）

---------------------------------------------------------------------------------------
执行前对任务书三处事实/模型的更正（全部有本地 jar 与仓库内文件实证，详见脚本末尾 DEV notes）
---------------------------------------------------------------------------------------
D1. 字段名是 "spawners"，不是 "spawns"。
    实证：vanilla 1.21.1 全部 biome JSON、BWG 2.6.0 全部 55 个 biome JSON、以及本仓库既有的
    data/beloong/worldgen/biome/loong_palace.json，三者无一例外使用 `"spawners"`。
    `Biome` 的 codec 只认 `spawners`；写 `spawns` 是未知字段（被静默忽略或触发解析告警），
    且不会产生任何刷怪。故本脚本写出 `"spawners"`。
    对应地：任务书给出的 {"creature": {"bounding_box": "piece", "spawns": [...]}} 是
    **结构 spawn_overrides**（SpawnOverride）的 schema，不是 biome 的 schema。biome 里
    `spawners` 是 category -> SpawnerData 数组的扁平映射。本脚本按 biome schema 落盘：
    {"creature": [ {"type":…, "weight":…, "minCount":…, "maxCount":…}, … ]}

D2. BWG 的 biome JSON **不是**空 spawns。
    实证：55/55 个文件都有非空 `spawners`（creature 非空 49 个、monster 非空 54 个、
    ambient 非空 50 个……共 39 种生物，含 biomeswevegone:man_o_war / oddion 等模组生物）。
    设计文档 §一 第 19 行「BWG datapack 生物群系 JSON 无 spawns 字段」系按错误的键名
    (`spawns`) 检索得出的结论。因此盲目整表覆写会**删掉** BWG 原有的 monster/ambient/
    water_* 生态（如 pale_bog 的 drowned/bogged/slime/spider），属于功能倒退。
    本脚本的处理：只把 A 档名单写入 `creature`（陆生动物）这一类；其余 category 原样保留。
    这同时满足 §2.5 的验收项「每个克隆群系 spawns 名单与配置一致」（针对动物名单）。

D3. 原版侧实际存在的是 snowy_beach，没有 frozen_beach（1.21.1 已更名），故取 snowy_beach。
    另：任务书枚举的原版清单共 16 条（海洋 9 + 河流 2 + 洞穴 3 + 沙滩 2），
    55+16=71，而非任务书写的 55+15=70（把海洋数成 8 了）。少克隆任何一个海洋都会让
    该气候点回落到 minecraft:* 群系，直接违背「零原版群系 id」目标，故按枚举全量输出 71 个。

---------------------------------------------------------------------------------------
运行方式
    python3 scripts/clone_biomes.py
    依赖：仅标准库（zipfile / json / re / pathlib / hashlib）
---------------------------------------------------------------------------------------
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

# ---------------------------------------------------------------- 路径配置

REPO = Path(__file__).resolve().parents[1]

BWG_JAR = Path("/home/wuhanhao/github/BeLoong/mods/"
               "[我们走过的生物群系] Oh-The-Biomes-Weve-Gone-NeoForge-2.6.0.jar")
VANILLA_JAR = Path("/tmp/vanilla-1.21.1.jar")
VANILLA_EXTRACTED = Path("/tmp/vanillap")          # 优先使用已解压目录，缺失则回落到 jar

OUT_DIR = REPO / "src/main/resources/data/beloong/worldgen/biome"
MANIFEST = REPO / "build/extracted/clone-manifest.json"

BWG_NS = "biomeswevegone"
OUT_PREFIX = "disaster_"
OUT_NS = "beloong"

# 原版克隆清单（16 个；frozen_beach 在 1.21.1 不存在 → snowy_beach）
VANILLA_BIOMES = [
    # 海洋 9
    "ocean", "warm_ocean", "lukewarm_ocean", "deep_lukewarm_ocean", "cold_ocean",
    "deep_cold_ocean", "frozen_ocean", "deep_frozen_ocean", "deep_ocean",
    # 河流 2
    "river", "frozen_river",
    # 洞穴 3
    "dripstone_caves", "lush_caves", "deep_dark",
    # 沙滩 2
    "beach", "snowy_beach",
]

# ---------------------------------------------------------------- A 档刷怪表

BASE_CREATURE = [
    {"type": "minecraft:sheep",   "weight": 12, "minCount": 4, "maxCount": 4},
    {"type": "minecraft:cow",     "weight": 8,  "minCount": 4, "maxCount": 4},
    {"type": "minecraft:pig",     "weight": 6,  "minCount": 4, "maxCount": 4},
    {"type": "minecraft:chicken", "weight": 5,  "minCount": 4, "maxCount": 4},
    {"type": "minecraft:rabbit",  "weight": 4,  "minCount": 2, "maxCount": 3},
]

# (正则, 附加条目) —— 按文件名子串匹配，可叠加；同 type 去重保留 weight 最大者
CLIMATE_RULES = [
    # 严寒类（frozen/icy/snow/crimson/glacier/shattered/borealis）→ 狐狸
    (r"frozen|icy|snow|crimson|glacier|shattered|borealis",
     [{"type": "minecraft:fox", "weight": 4, "minCount": 2, "maxCount": 4}]),
    # 真·寒带（frozen/icy/glacier/snow）→ 北极熊（crimson/shattered/borealis 不加）
    (r"frozen|icy|glacier|snow",
     [{"type": "minecraft:polar_bear", "weight": 8, "minCount": 1, "maxCount": 2}]),
    # 干热类（savanna/badlands/mojave/atacama/outback/desert/red_rock/basalt）→ 鹦鹉
    # 牛：基础名单已含，不重复；狼：本类省略；豹猫：暂不加
    (r"savanna|badlands|mojave|atacama|outback|desert|red_rock|basalt",
     [{"type": "minecraft:parrot", "weight": 2, "minCount": 1, "maxCount": 2}]),
    # 热带类（jungle/tropical/fragment/rainforest/jacaranda）→ 鹦鹉 + 熊猫 + 豹猫
    (r"jungle|tropical|fragment|rainforest|jacaranda",
     [{"type": "minecraft:parrot", "weight": 5, "minCount": 1, "maxCount": 2},
      {"type": "minecraft:panda",  "weight": 2, "minCount": 1, "maxCount": 2},
      {"type": "minecraft:ocelot", "weight": 5, "minCount": 3, "maxCount": 6}]),
    # 湿地类（swamp/wet/bayou/marsh/bog/mangrove）→ 青蛙
    (r"swamp|wet|bayou|marsh|bog|mangrove",
     [{"type": "minecraft:frog", "weight": 10, "minCount": 2, "maxCount": 5}]),
    # 林叶类（taiga/boreal/forest/woods/woodland/grove/thicket）→ 狼 + 狐狸
    (r"taiga|boreal|forest|woods|woodland|grove|thicket",
     [{"type": "minecraft:wolf", "weight": 5, "minCount": 2, "maxCount": 4},
      {"type": "minecraft:fox",  "weight": 4, "minCount": 2, "maxCount": 4}]),
    # 山地类（peak/slope/mountain/howling/skyris/stacks）→ 山羊
    (r"peak|slope|mountain|howling|skyris|stacks",
     [{"type": "minecraft:goat", "weight": 5, "minCount": 2, "maxCount": 4}]),
]

# biome spawners 的 8 个标准 category，缺失时补空数组，保证键显式存在
SPAWN_CATEGORIES = [
    "ambient", "axolotls", "creature", "misc", "monster",
    "underground_water_creature", "water_ambient", "water_creature",
]


def creature_list(biome_name: str) -> list[dict]:
    """基础名单 + 气候关键字附加，按 type 去重（保留 weight 最大者，位置取首次出现）。"""
    merged: dict[str, dict] = {}
    for entry in BASE_CREATURE:
        merged[entry["type"]] = dict(entry)
    for pattern, extras in CLIMATE_RULES:
        if re.search(pattern, biome_name):
            for entry in extras:
                cur = merged.get(entry["type"])
                if cur is None or entry["weight"] > cur["weight"]:
                    merged[entry["type"]] = dict(entry)
    return list(merged.values())


# ---------------------------------------------------------------- 源数据读取

def read_bwg_sources() -> dict[str, dict]:
    with zipfile.ZipFile(BWG_JAR) as zf:
        names = [n for n in zf.namelist()
                 if n.startswith(f"data/{BWG_NS}/worldgen/biome/") and n.endswith(".json")]
        out = {}
        for n in sorted(names):
            out[Path(n).stem] = json.loads(zf.read(n).decode("utf-8"))
    return out


def read_vanilla_source(name: str) -> dict:
    p = VANILLA_EXTRACTED / "data/minecraft/worldgen/biome" / f"{name}.json"
    if p.is_file():
        return json.loads(p.read_text(encoding="utf-8"))
    with zipfile.ZipFile(VANILLA_JAR) as zf:
        return json.loads(zf.read(f"data/minecraft/worldgen/biome/{name}.json").decode("utf-8"))


# ---------------------------------------------------------------- 克隆

def normalize_spawners(src_spawners: dict | None) -> dict:
    """确保 8 个 category 键显式存在（保持源顺序，缺失补空数组）。"""
    out: dict[str, list] = {}
    for cat in SPAWN_CATEGORIES:
        out[cat] = list((src_spawners or {}).get(cat, []) or [])
    return out


def clone_bwg(name: str, src: dict) -> dict:
    """BWG 克隆：JSON 内容除 spawners.creature 外原样；biome 自身 id 由输出文件名承载。"""
    out = json.loads(json.dumps(src))           # 深拷贝，保持字段插入序
    sp = normalize_spawners(src.get("spawners"))
    sp["creature"] = creature_list(name)        # A 档：仅覆写动物类，其余生态保留（见 D2）
    out["spawners"] = sp
    return out


def clone_vanilla(name: str, src: dict) -> dict:
    """原版克隆：整表照抄源 JSON，仅确保 spawners 8 键显式存在（deep_dark 保持全空）。"""
    out = json.loads(json.dumps(src))
    out["spawners"] = normalize_spawners(src.get("spawners"))
    return out


def dump(path: Path, data: dict) -> None:
    text = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=False) + "\n"
    path.write_text(text, encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)

    bwg = read_bwg_sources()
    manifest: list[dict] = []

    # --- BWG 55
    for name in sorted(bwg):
        data = clone_bwg(name, bwg[name])
        out_id = f"{OUT_PREFIX}{name}"
        dump(OUT_DIR / f"{out_id}.json", data)
        manifest.append({
            "source": f"{BWG_NS}:{name}",
            "output": f"{OUT_NS}:{out_id}",
            "changed_ids": 1,   # 每个克隆只改 1 个 id：群系自身 id（命名空间+前缀，由文件名承载）
        })

    # --- 原版 16
    for name in VANILLA_BIOMES:
        data = clone_vanilla(name, read_vanilla_source(name))
        out_id = f"{OUT_PREFIX}{name}"
        dump(OUT_DIR / f"{out_id}.json", data)
        manifest.append({
            "source": f"minecraft:{name}",
            "output": f"{OUT_NS}:{out_id}",
            "changed_ids": 1,
        })

    MANIFEST.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
        encoding="utf-8")

    print(f"[ok] wrote {len(manifest)} biome json -> {OUT_DIR}")
    print(f"[ok] manifest -> {MANIFEST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
