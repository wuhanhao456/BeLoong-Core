# 天灾维度群系重制设计 v2（命运空间：全 beloong 命名空间 + 探险罗盘维度过滤）

> 状态：**设计稿 v2，待审查**
> 日期：2026-09-11（v2 同日修订）
> 决策已确认（wuhanhao，2026-09-11）：
> 1. 保留洞穴/地形 → 新命名空间方案，不删地形引擎，只换群系构成
> 2. 探险罗盘假结构 → 方案 2：beloong core mixin 维度过滤
> 3. 地表群系像对像映射；水域和洞穴也换；提交必须落在 wuhanhao456 fork
> 4. **v2 追加**：目标改为「命运空间」完全体——天灾维度**零原版群系 id**，防止原版结构/原版生物借群系匹配漏进天灾。选项 2（完全体）已拍板。

---

## 一、机制背景（1.21.1 事实，全部本地 jar 核实）

- **地形与群系是两套系统**：地形起伏、洞穴、矿物雕刻由 `noise_settings` 的 noise_router/density_function 决定；`multi_noise` biome source 只决定气候点 → 群系映射。换群系 id 不丢洞穴与矿物。
- **1.21.1 关键变化**：原版 `multi_noise_biome_source_parameter_list/overworld.json` 只含 `{"preset":"minecraft:overworld"}`（下载原版 1.21.1 client.jar 逐字节核实，mcmeta data-json 分支一致）。参数条目在代码注册表内，**无 datapack JSON 载体** → 自定义 preset 必须内联完整 parameterList，条目数据需实现阶段运行时 dump / 映射 jar 提取。
- **结构/生物的生成过滤就是群系 id 匹配**：原版 34 个 structure 的 `biomes` 字段写死原版群系或原版 tag（矿井含 `dripstone_caves`/`lush_caves`，试炼密室含 50+ 原版群系）；原版群系的刷怪表（spawns）也随群系定义走。**把维度内出现的群系 id 全换成自有 id，原版结构/原版刷怪表即全部失配绝迹，无需任何过滤代码。**
- **BWG 的联动细节（v2 关键证据）**：BWG datapack 把自家群系塞进了 **17 个原版结构的白名单 tag**（实测：`village_plains` → 仅 3 个 BWG 群系；`trial_chambers` → `#biomeswevegone:overworld`；`pillager_outpost` → 11 个 BWG 群系；`shipwreck`/`igloo` → 各 2 个；`buried_treasure` → `#biomeswevegone:ocean`；另有 is_overworld/is_ocean 等 biome tag 同理）。这些 tag 引用全部是 `biomeswevegone:` 前缀——**直接用 `biomeswevegone:*` 群系时这 17 个原版结构照样进天灾（档 1 的口子）；克隆成 `beloong:*` 后这些补丁不命中，原版结构归零（档 2 完全体）**。
- **BWG datapack 生物群系 JSON 无 spawns 字段**（55 个文件逐一核实，`spawns` 全空）——BWG 群系的动物刷怪表在 **BWG 代码里、按 `biomeswevegone:` 群系 key 注册**。克隆改 id 后 BWG 的 spawns 注册查不到新 key → **克隆群系若不手写 spawns 就没有动物**。这是档 2 最重要的隐藏成本。
- BWG biome JSON 的 feature 引用统计：55 个群系共 2836 个 feature 引用，其中 `minecraft:*` 2453（矿物/ decorations/湖泊/紫水晶洞等）、`biomeswevegone:*` 383。**引用原版 feature 资源不破坏 id 隔离**——隔离对象是群系 id（结构/刷怪/生物群系标签的匹配键），不是 feature 资源。洞穴雕刻（carvers）同理：`minecraft:cave` / `cave_extra_underground` / `canyon` 照常引用。
- BWG 自家 `ocean` tag 只有 `dead_sea` + `lush_stacks`（非纯海洋群系）→ 纯海洋必须自建。

## 二、目标构成（档 2 完全体）

天灾维度内出现的**每一个群系 id 都是 `beloong:disaster_*`**：

| 层 | 群系 | 来源 | spawns |
|---|---|---|---|
| 地表陆生 | 55 个，克隆自 BWG 同名 | 复制 BWG JSON → 改 id | **手写**（见 2.3） |
| 纯海洋 | 约 10 个（warm/deep~frozen 全档），克隆自原版海洋群系 | 复制原版 JSON → 改 id，features/effects 原样 | 手写（drowned/发光鱿鱼/鱼按需） |
| 河流/冻河 | 2 个，克隆自原版 river/frozen_river | 同上 | 手写（squid/Salmon 类） |
| 洞穴 | 3 个（dripstone_caves / lush_caves / deep_dark），克隆自原版 | 同上； lush_caves 保留其水生生物特性 | 手写（蝙蝠/史莱姆/深暗行怪按需） |

合计约 **70 个群系 JSON**，全部在 `data/beloong/worldgen/biome/`（新目录，不与现有 `kubejs/data/beloong/` 混淆；core 与整合包的归属在实现阶段定，倾向 core——见 §5）。

### 2.1 保留的"原版"到底是什么

零原版**群系 id** ≠ 零原版**数据资源**。以下引用照旧指向 `minecraft:` 资源，属于预期行为而非"原版的东西漏进来"：

- 地形引擎：自有 `noise_settings/beloong:disaster` 的 noise_router 内部引用原版 density_function / noise 资源（按 ID 引用，结构形状/洞穴雕刻/矿脉全保留）
- features/carvers：矿物、溶洞石、滴水石、紫水晶洞等原版 placed_feature（洞穴与矿物的来源）
- 音乐/音效/粒子：BWG JSON 内引用的 `biomeswevegone:music.*` 等

### 2.2 新增/修改文件清单（全部 beloong 命名空间，BeLoong-Core 内）

| 文件 | 内容 |
|---|---|
| `data/beloong/multi_noise_biome_source_parameter_list/disaster.json` | 内联完整 parameterList；气候区间照搬原版条目（运行时 dump 提取），`biome` 全部指 `beloong:disaster_*`；水域/洞穴点位的区间照抄、群系指向自有克隆 |
| `data/beloong/worldgen/noise_settings/disaster.json` | 原版 overworld 的完整拷贝；内部引用按 ID 原样指向 `minecraft:*` 资源；sea_level 63 / aquifers / ore_veins 照旧 |
| `data/beloong/dimension/disaster.json` | `settings` → `beloong:disaster`；`preset` → `beloong:disaster` |
| `data/beloong/worldgen/biome/disaster_*.json` | 约 70 个群系（地表 BWG 克隆 + 洞穴/海洋/河流克隆），spawns 手写 |
| `data/beloong/tags/worldgen/biome/is_disaster.json` | 改指 `#beloong:disaster_*` 全集（此文件现居整合包 kubejs，迁移或双写见 §5） |

### 2.3 spawns 手写策略（待 wuhanhao 最后拍板项）

BWG 的动物表按 `biomeswevegone:` key 注册，克隆后失效。两档做法：

- **A 省事档**：全部手写统一基础名单（牛/羊/猪/鸡/兔 + 各气候附加：狼/狐狸/北极熊/鹦鹉/海龟…按群系气候粗配），一次脚本生成，生物构成"合理但非逐群系精调"
- **B 完全可控档**：逐群系按 BWG 原版氛围配名单（如 maple_taiga 配狼+狐狸+兔，bayou 配青蛙+鹦鹉热...），工作量约 +1 天，生物构成完全写死

### 2.4 联动与风险

- **TerraBlender 注入退路**：档 2 后 preset 内条目已是 `beloong:` id，TB 注入的 `biomeswevegone:*` 气候点仍会追加（无害重复或落空）。若实测 BWG 表面规则/音乐在新 key 下异常，则把天灾从 `terrablender:overworld_regions` tag 摘除，TB 注入链整体退役（CloneParameterListMixin 一并冗余化）。**两条路都能走通，实测择一**，这是阶段 1 实测的最重点。
- **`is_disaster` tag 消费方**：cataclysm 8 竞技场 + fdbosses 3 竞技场 + disaster_set/disaster_set_ground 的结构引用该 tag，改指自有群系后结构照常匹配（tag 内值换而已）。
- **原版结构退场清单**（档 2 预期全部消失）：村庄/前哨站/矿井/沉船/海底神殿/试炼密室/远古城市/locking 罗盘名单里全部原版结构 + 17 个 BWG 联动结构。**disaster_set 内 mss/netherman 等模组结构若引用 `#beloong:is_disaster` 则保留**（引用BWG 群系的会随 BWG 克隆同步退场，逐个核对是阶段 1 实测重点清单）。
- 旧存档已生成区块不重生成；验证看新区块或重置维度。

### 2.4.1 同步与防漂移（档 2 特有）

- 克隆脚本（Python，进仓库 `scripts/`）从 BWG jar 提取 55 个群系 JSON → 改 id 前缀 → 哈希落盘；BWG 升级时重跑 + 哈希比对防漏（沿用 wuhanhao「runtime-sync-check 防静默不一致」纪律）
- spawns 名单独立成 `scripts/spawn_overrides.yaml`，与克隆解耦，改生物不动结构

### 2.5 验收标准

新区块抽样（区块 NBT palette，复用总设计文档 4.5 方法）：

- 群系 `minecraft:*` 命中 = 0（全维度，含地下与水域——这次真的 0）
- `dripstone_caves`/`lush_caves` 洞穴生态在地下抽样可见；矿物照常
- 天灾维度 `/locate` 原版结构（村庄/沉船/矿井/试炼密室）= 无命中
- 罗盘主世界列表无天灾结构（阶段 2 合并验证）；天灾内 cataclysm/fdbosses 搜索实际命中
- 每个克隆群系 spawns 名单与配置一致（抽查对照 yaml）

## 三、问题 B：探险罗盘假结构（不变，随 v2 一起实施）

结论同 v1：`StructureUtilsMixin`（`@Pseudo`，拦 `getAllowedStructureKeys` 的 RETURN，按 `structure.biomes() ∩ 当前维度 possibleBiomes ≠ ∅` 过滤）。v2 下此过滤仍有价值——它同时清掉主世界列表里其他维度的假条目，与 A 互补。

## 四、阶段

| 阶段 | 内容 |
|---|---|
| 0 | 原版 parameterList 条目运行时提取 + 校验（条目数/区间连续性） |
| 1 | 克隆脚本 + 70 群系 + 3 核心文件 + spawns yaml + 实测（TB 注入行为、结构退场清单、罗盘/locate 交叉验证） |
| 2 | StructureUtilsMixin + 回归 |
| 收尾 | `docs/天灾维度总设计.md` 同步、整合包侧 `is_disaster` tag 迁移 |

提交全部推 `origin = wuhanhao456/BeLoong-Core`（fork），上游不触。

## 五、待定项（实现前需拍板）

1. **spawns 策略**：§2.3 的 A（统一基础名单）还是 B（逐群系精调）——影响工作量约一天
2. `is_disaster` tag 文件放 core 还是留整合包（涉及「原版 + 本仓库 = 完美复现」纪律的边界，倾向随 core 走、整合包删除）
3. TB 注入实测若走「摘除 tag」路线，`terrablender:overworld_regions` 的 `replace:true` 文件在 core 内还是整合包内需统一归属


## 勘误 v3（2026-09-11 实测 log 后修正）

**参数表不能做成独立注册项**（原 v2 方案 §T1d 作废）：

- `MultiNoiseBiomeSourceParameterList.DIRECT_CODEC` = `Preset.CODEC.fieldOf("preset")` + `RegistryOps.retrieveGetter(BIOME)`；
  `Preset.CODEC` 走 `ResourceLocation.CODEC.flatXmap`，`BY_NAME` 只有 `minecraft:overworld` / `minecraft:nether`。
  → 该注册表的注册项**无法承载自定义 parameters**，只能是 `{"preset":"minecraft:overworld"}` 这种别名。
  写 `{"parameters":[...]}` 会两个分支都报 `No key preset` → registry 加载失败 → 开世界黑屏（f6f19d6 后实测）。
- 正确做法：`MultiNoiseBiomeSource.CODEC = Codec.mapEither(
    Climate.ParameterList.codec(Biome.CODEC.fieldOf("biome")).fieldOf("biomes"),   # 内联分支，优先
    MultiNoiseBiomeSourceParameterList.CODEC.fieldOf("preset"))`
  → **7593 条参数表内联进 `dimension/disaster.json` 的 `generator.biome_source.biomes`**，删除独立注册项文件。
- 条目结构（`Climate.ParameterPoint.CODEC` 7 键嵌在 `parameters` 下，`biome` 与其平级）：
  `{"parameters":{"temperature":[lo,hi],"humidity":[..],"continentalness":[..],"erosion":[..],"depth":[..],"weirdness":[..],"offset":0.0},"biome":"beloong:disaster_xxx"}`
- 生成脚本：`scripts/build_disaster_dimension.py`（取代 `build_disaster_preset.py`）。
