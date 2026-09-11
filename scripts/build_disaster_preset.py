#!/usr/bin/env python3
"""T1d: 生成 beloong:disaster 多维噪声参数表（命运空间完全体）。

输入: build/extracted/overworld-parameters-1.21.1.json (7593 条原版条目, 运行时反射提取, 见 extraction-report.md)
输出: src/main/resources/data/beloong/multi_noise_biome_source_parameter_list/disaster.json
      顶层格式 {"parameters": [point...]}（1.21.1 codec 实证: Climate$ParameterList codec 为 pointCodec.fieldOf("parameters") 包装,
      已反混淆 def$c/def$d 字节码核证; 每个 point = {biome, temperature, humidity, continentalness, erosion, depth, weirdness, offset}）

映射规则（像对像, wuhanhao 2026-09-11 确认）:
- 16 个自有克隆群系（海洋9/河2/洞3/beach2）: 气候点原样继承原版对应群系, 仅改 id 为 beloong:disaster_同名
- 其余 37 个原版地表群系: 按气候等价原则映射到 55 个 beloong:disaster_BWG 群系（映射表见 VANILLA_TO_BWG）
- 未映射到的 BWG 群系不出现在 preset(纯点替换, 不新增点位) —— BWG 全覆盖靠 TerraBlender 注入或后续点位扩充, 与主会话设计一致
"""
import json, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, 'build/extracted/overworld-parameters-1.21.1.json')
OUT = os.path.join(REPO, 'src/main/resources/data/beloong/multi_noise_biome_source_parameter_list/disaster.json')

# 16 个自有克隆（1:1 改名）
SELF_CLONES = [
    'ocean','warm_ocean','lukewarm_ocean','deep_lukewarm_ocean','cold_ocean','deep_cold_ocean',
    'frozen_ocean','deep_frozen_ocean','deep_ocean',
    'river','frozen_river',
    'dripstone_caves','lush_caves','deep_dark',
    'beach','snowy_beach',
]

# 37 个原版地表群系 → BWG 像对像映射（气候等价: 温度/湿度档位对应, 单调可辩护）
VANILLA_TO_BWG = {
    'plains': 'prairie',
    'sunflower_plains': 'rose_fields',
    'savanna': 'baobab_savanna',
    'savanna_plateau': 'allium_shrubland',
    'windswept_savanna': 'araucaria_savanna',
    'jungle': 'tropical_rainforest',
    'sparse_jungle': 'jacaranda_jungle',
    'bamboo_jungle': 'fragment_jungle',
    'desert': 'windswept_desert',
    'badlands': 'rugged_badlands',
    'eroded_badlands': 'sierra_badlands',
    'wooded_badlands': 'red_rock_valley',
    'snowy_plains': 'crimson_tundra',
    'ice_spikes': 'shattered_glacier',
    'snowy_taiga': 'frosted_taiga',
    'taiga': 'aspen_boreal',
    'old_growth_pine_taiga': 'coniferous_forest',
    'old_growth_spruce_taiga': 'black_forest',
    'old_growth_birch_forest': 'zelkova_forest',
    'birch_forest': 'maple_taiga',          # 桦木林气候带对应温带木群系
    'forest': 'temperate_grove',
    'flower_forest': 'rose_fields',
    'dark_forest': 'ebony_woods',
    'swamp': 'cypress_wetlands',
    'mangrove_swamp': 'white_mangrove_marshes',
    'stony_shore': 'dacite_shore',
    'windswept_hills': 'howling_peaks',
    'windswept_gravelly_hills': 'red_rock_peaks',
    'windswept_forest': 'overgrowth_woodlands',
    'snowy_slopes': 'frosted_coniferous_forest',
    'grove': 'frosted_coniferous_forest',
    'frozen_peaks': 'eroded_borealis',
    'jagged_peaks': 'skyris_vale',
    'stony_peaks': 'ironwood_gour',
    'meadow': 'orchard',
    'cherry_grove': 'sakura_grove',
    'mushroom_fields': 'pale_bog',          # 蘑菇岛孤绝群系; 用气候最接近的孤立湿地 BWG 群系
}

def main():
    params = json.load(open(SRC))['parameters']
    n = len(params)
    out = []
    misses = {}
    for e in params:
        b = e['biome'].split(':')[1]  # 已确证 53 群系全带 minecraft: 前缀
        if b in SELF_CLONES:
            newb = f'beloong:disaster_{b}'
        elif b in VANILLA_TO_BWG:
            newb = f'beloong:disaster_{VANILLA_TO_BWG[b]}'
        else:
            misses[b] = misses.get(b, 0) + 1
            continue
        p = dict(e)
        p['biome'] = newb
        out.append(p)
    if misses:
        print('UNMAPPED vanilla biomes (climate points dropped):', misses, file=sys.stderr)
    # 自检: 输出中引用的每个群系必须有对应克隆文件
    biome_dir = os.path.join(REPO, 'src/main/resources/data/beloong/worldgen/biome')
    have = {f[len('disaster_'):-5] for f in os.listdir(biome_dir)
            if f.startswith('disaster_') and f.endswith('.json')}
    used = {p['biome'].split(':')[1][len('disaster_'):] for p in out}
    missing = used - have
    if missing:
        print('ERROR: preset references biomes without clone files:', sorted(missing), file=sys.stderr)
        sys.exit(1)
    # 区间合法性快速复检
    for p in out:
        for ax in ('temperature','humidity','continentalness','erosion','depth','weirdness'):
            lo, hi = p[ax]
            assert lo <= hi, (p['biome'], ax)
    payload = {'parameters': out}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write('\n')
    # 回读自检
    check = json.load(open(OUT))
    assert len(check['parameters']) == len(out)
    used_biomes = sorted({p['biome'] for p in check['parameters']})
    print(f'entries: {len(out)} (in {n})')
    print(f'biomes referenced: {len(used_biomes)}')
    print('missing clones: none' if not missing else 'MISSING: ' + str(missing))
    print(f'written: {OUT}')
    print('self-check: parse OK, range OK, clone-coverage OK')

if __name__ == '__main__':
    main()
