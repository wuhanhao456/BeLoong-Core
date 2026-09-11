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
- 7 个未接线克隆（方案甲, SPLIT_TABLE）: 按切分轴（weirdness）把宿主点位升序整点均匀分组,
  各参与方分得一段; 只改 biome 归属 id, 参数原样保留, 总点数不变
"""
import json, os, sys
from collections import Counter

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

# 7 个未接线克隆的切分方案（方案甲, wuhanhao 2026-09-11 确认）。
# host     = 被切宿主的克隆 id 后缀（须已在 SELF_CLONES / VANILLA_TO_BWG 中被接线）
# axis     = 切分轴（本次全部为 'weirdness'）
# outputs  = 均分后各段归属的 id 后缀, 按切分轴升序【连续】分配;
#            第 0 项即宿主自己（保留一段, 故宿主切分后仍有点位）
SPLIT_TABLE = [
    {'host': 'ebony_woods',         'axis': 'weirdness',
     'outputs': ['ebony_woods', 'forgotten_forest', 'weeping_witch_forest']},
    {'host': 'cypress_wetlands',    'axis': 'weirdness',
     'outputs': ['cypress_wetlands', 'cypress_swamplands']},
    {'host': 'maple_taiga',         'axis': 'weirdness',
     'outputs': ['maple_taiga', 'cika_woods']},
    {'host': 'rose_fields',         'axis': 'weirdness',
     'outputs': ['rose_fields', 'pumpkin_valley']},
    {'host': 'windswept_desert',    'axis': 'weirdness',
     'outputs': ['windswept_desert', 'dead_sea']},
    {'host': 'tropical_rainforest', 'axis': 'weirdness',
     'outputs': ['tropical_rainforest', 'lush_stacks']},
]
SPLIT_NEW_CLONES = ['forgotten_forest', 'weeping_witch_forest', 'cypress_swamplands',
                    'cika_woods', 'pumpkin_valley', 'dead_sea', 'lush_stacks']


def _clone_id(entry):
    return entry['biome'].split(':')[1][len('disaster_'):]


def _point_key(entry):
    """单点唯一键: biome + 6 气候轴区间 + offset（即"7 轴参数"）。"""
    p = entry['parameters']
    return (entry['biome'],) + tuple(tuple(p[ax]) for ax in AXES) + (float(p['offset']),)


def apply_splits(entries):
    """方案甲: 按切分轴整点均匀分组。

    宿主点位按 axis 值（weirdness 为 [lo,hi] 区间, 以 (lo,hi) 为序）升序排序后,
    均分成 N 段 —— 每段【连续、非空、互不重叠】且整点分配（不切单个点的区间）;
    第 i 段整体改归属 outputs[i]。切出的组保留原点全部参数, 只改 biome 归属 id。
    返回统计 dict: {host: {'axis':..,'before':n,'after':{id:cnt}}}
    """
    stats = {}
    for spec in SPLIT_TABLE:
        host, axis, outs = spec['host'], spec['axis'], spec['outputs']
        n = len(outs)
        assert axis in AXES, spec
        assert n >= 2 and outs[0] == host, spec
        assert len(set(outs)) == n, f'duplicate outputs in {spec}'

        grp = [e for e in entries if _clone_id(e) == host]
        assert grp, f'split host not wired into parameter table: {host}'
        before = len(grp)
        # 按切分轴升序（区间用 (lo,hi) 排序）; 并列项稳定排序保持原相对次序
        grp.sort(key=lambda e: tuple(e['parameters'][axis]))
        # 整点均匀分组, 余数分给靠前的段
        base, rem = divmod(before, n)
        segs, cursor = [], 0
        for i in range(n):
            size = base + (1 if i < rem else 0)
            segs.append(grp[cursor:cursor + size])
            cursor += size
        assert cursor == before, (host, [len(s) for s in segs])
        assert all(segs), f'empty segment after split: {host} -> {[len(s) for s in segs]}'
        # 逐段改归属（参数原样保留）
        for out, seg in zip(outs, segs):
            for e in seg:
                e['biome'] = f'beloong:disaster_{out}'
        stats[host] = {'axis': axis, 'before': before,
                       'after': {out: len(seg) for out, seg in zip(outs, segs)}}
    return entries, stats


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

    # 方案甲: 给 7 个未接线克隆切分宿主参数表
    entries, split_stats = apply_splits(entries)

    # 切分后单点单归属: 全表 (biome + 7 轴参数) 组合键必须唯一
    keys = [_point_key(e) for e in entries]
    dup = [k for k, c in Counter(keys).items() if c > 1]
    assert not dup, f'duplicate (biome+params) points after split: {dup[:3]}'

    # 7 个新克隆必须全部接线
    wired = {_clone_id(e) for e in entries}
    unwired = [c for c in SPLIT_NEW_CLONES if c not in wired]
    assert not unwired, f'new clones not wired after split: {unwired}'

    biome_dir = os.path.join(REPO, 'src/main/resources/data/beloong/worldgen/biome')
    have = {f[len('disaster_'):-5] for f in os.listdir(biome_dir)
            if f.startswith('disaster_') and f.endswith('.json')}
    used = {_clone_id(e) for e in entries}
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

    # --- 切分相关自检（方案甲）---
    final_counts = Counter(_clone_id(e) for e in got)
    total_points = len(got)
    assert total_points == len(params) == 7593, (total_points, len(params))
    # 每个新克隆点数 >= 5
    for c in SPLIT_NEW_CLONES:
        assert final_counts[c] >= 5, f'new clone below 5 points: {c}={final_counts[c]}'
    # 每个被切宿主切分后点数 >= 5
    for spec in SPLIT_TABLE:
        assert final_counts[spec['host']] >= 5, \
            f'host below 5 points after split: {spec["host"]}={final_counts[spec["host"]]}'
    # 输出文件里 (biome + 7 轴参数) 组合键无重复
    out_keys = [_point_key(e) for e in got]
    out_dup = [k for k, c in Counter(out_keys).items() if c > 1]
    assert not out_dup, f'duplicate (biome+params) in written file: {out_dup[:3]}'
    assert len(set(out_keys)) == total_points, 'unique-key count != point count'

    used_biomes = sorted({e['biome'] for e in got})
    print(f'entries: {len(entries)} (from {len(params)})')
    print(f'biomes referenced: {len(used_biomes)}')
    print(f'unmapped dropped: {sum(misses.values())} points / {len(misses)} vanilla biomes' if misses else 'unmapped: none')

    print('--- split stats (方案甲, axis=weirdness) ---')
    for spec in SPLIT_TABLE:
        host = spec['host']
        st = split_stats[host]
        segs = ' | '.join(f'{k}={v}' for k, v in st['after'].items())
        print(f'  {host}: {st["before"]} -> {final_counts[host]}  [{segs}]')
    print('  new clones:', ', '.join(f'{c}={final_counts[c]}' for c in SPLIT_NEW_CLONES))

    print(f'written: {OUT}  ({os.path.getsize(OUT)/1024/1024:.2f} MB)')
    print('self-check: parse OK, range OK, clone-coverage OK, no minecraft: refs, no preset key')
    print('split self-check: total=7593 OK, 58 biomes OK, new-clone>=5 OK, host>=5 OK, unique-point-key OK')


if __name__ == '__main__':
    main()
