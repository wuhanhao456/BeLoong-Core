#!/usr/bin/env python3
"""T1d-v3: 生成 beloong:disaster 维度的内联多维噪声参数表（命运空间完全体）。

为什么内联而不是独立注册项（1.21.1 实证, 2026-09-11 日志 f6f19d6 之后）:
- MultiNoiseBiomeSourceParameterList.DIRECT_CODEC = Preset.CODEC.fieldOf("preset") + RegistryOps.retrieveGetter(BIOME)
  Preset.CODEC = ResourceLocation.CODEC.flatXmap(...) 且 BY_NAME 只含 minecraft:overworld / minecraft:nether。
  => 该注册表的注册项 **无法承载自定义 parameters**, 只能是 {"preset":"minecraft:overworld"} 这种别名。
  => 之前写在 data/beloong/worldgen/multi_noise_biome_source_parameter_list/disaster.json 的
     {"parameters":[...]} 两个分支都报 "No key preset" -> registry 加载失败 -> 开世界黑屏。
- MultiNoiseBiomeSource.CODEC = Codec.mapEither(
      Climate.parseList.codec(Biome.CODEC.fieldOf("biome")).fieldOf("biomes"),   # 内联分支（第一优先）
      MultiNoiseBiomeSourceParameterList.CODEC.fieldOf("preset")                # 预设分支
  )
  => 维度文件里直接内联 7593 条即可, 完全不需要该注册表。

输入: build/extracted/overworld-parameters-1.21.1.json (7593 条原版条目, 反射提取, 见 extraction-report.md)
输出: src/main/resources/data/beloong/dimension/disaster.json
      generator.biome_source = {"type":"minecraft:multi_noise","biomes":[
          {"parameters":{"temperature":[..],"humidity":[..],"continentalness":[..],
                         "erosion":[..],"depth":[..],"weirdness":[..],"offset":0.0},
           "biome":"beloong:disaster_xxx"}, ... ]}
      (Climate.ParameterPoint.CODEC 的 7 个键嵌在 "parameters" 下, biome 与 parameters 平级 —— 逐字段核过源码)

映射规则（像对像, wuhanhao 2026-09-11 确认）:
- 16 个自有克隆群系（海洋9/河2/洞3/beach2）: 气候点原样继承原版对应群系, 仅改 id 为 beloong:disaster_同名
- 其余 37 个原版地表群系: 按气候等价原则映射到 beloong:disaster_BWG 群系（VANILLA_TO_BWG）
- 未映射到的 BWG 群系不出现在参数表（纯点替换, 不新增点位）
"""
import json, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, 'build/extracted/overworld-parameters-1.21.1.json')
OUT = os.path.join(REPO, 'src/main/resources/data/beloong/dimension/disaster.json')
AXES = ('temperature', 'humidity', 'continentalness', 'erosion', 'depth', 'weirdness')

# 16 个自有克隆（1:1 改名）
SELF_CLONES = [
    'ocean', 'warm_ocean', 'lukewarm_ocean', 'deep_lukewarm_ocean', 'cold_ocean', 'deep_cold_ocean',
    'frozen_ocean', 'deep_frozen_ocean', 'deep_ocean',
    'river', 'frozen_river',
    'dripstone_caves', 'lush_caves', 'deep_dark',
    'beach', 'snowy_beach',
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
    'birch_forest': 'maple_taiga',
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
    'mushroom_fields': 'pale_bog',
}


def build_entries():
    params = json.load(open(SRC))['parameters']
    out, misses = [], {}
    for e in params:
        b = e['biome'].split(':')[1]
        if b in SELF_CLONES:
            newb = f'beloong:disaster_{b}'
        elif b in VANILLA_TO_BWG:
            newb = f'beloong:disaster_{VANILLA_TO_BWG[b]}'
        else:
            misses[b] = misses.get(b, 0) + 1
            continue
        for ax in AXES:
            lo, hi = e[ax]
            assert lo <= hi, (b, ax)
        out.append({
            'parameters': {ax: e[ax] for ax in AXES} | {'offset': float(e.get('offset', 0.0))},
            'biome': newb,
        })
    return params, out, misses


def main():
    params, entries, misses = build_entries()
    if misses:
        print('UNMAPPED vanilla biomes (climate points dropped):', misses, file=sys.stderr)

    biome_dir = os.path.join(REPO, 'src/main/resources/data/beloong/worldgen/biome')
    have = {f[len('disaster_'):-5] for f in os.listdir(biome_dir)
            if f.startswith('disaster_') and f.endswith('.json')}
    used = {e['biome'].split(':')[1][len('disaster_'):] for e in entries}
    missing = used - have
    if missing:
        print('ERROR: biome_source references biomes without clone files:', sorted(missing), file=sys.stderr)
        sys.exit(1)

    body = ',\n'.join('        ' + json.dumps(e, ensure_ascii=False, separators=(',', ':')) for e in entries)
    text = (
        '{\n'
        '  "type": "beloong:disaster",\n'
        '  "generator": {\n'
        '    "type": "minecraft:noise",\n'
        '    "settings": "beloong:disaster",\n'
        '    "biome_source": {\n'
        '      "type": "minecraft:multi_noise",\n'
        '      "biomes": [\n' + body + '\n      ]\n'
        '    }\n'
        '  }\n'
        '}\n'
    )
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w') as f:
        f.write(text)

    check = json.load(open(OUT))
    bs = check['generator']['biome_source']
    assert bs['type'] == 'minecraft:multi_noise'
    assert 'preset' not in bs, 'preset 键不得与内联 biomes 共存'
    got = bs['biomes']
    assert len(got) == len(entries), (len(got), len(entries))
    assert all(set(e['parameters']) == set(AXES) | {'offset'} for e in got)
    assert not any(e['biome'].startswith('minecraft:') for e in got)
    used_biomes = sorted({e['biome'] for e in got})
    print(f'entries: {len(entries)} (from {len(params)})')
    print(f'biomes referenced: {len(used_biomes)}')
    print(f'unmapped dropped: {sum(misses.values())} points / {len(misses)} vanilla biomes' if misses else 'unmapped: none')
    print(f'written: {OUT}  ({os.path.getsize(OUT)/1024/1024:.2f} MB)')
    print('self-check: parse OK, range OK, clone-coverage OK, no minecraft: refs, no preset key')


if __name__ == '__main__':
    main()
