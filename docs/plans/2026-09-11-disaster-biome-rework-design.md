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

## 实施记录（2026-09-11 落地，Wu）

**0. 机制勘误（2026-09-11 二次核实）——本条结论已作废，同日第三次核对后推翻；正确结论见第 6 节**

1.21.1 的 tag 合并实际行为（`MultiPackResourceManager` + `FallbackResourceManager.getResourceStack` + `TagLoader.load` 逐处核对）：
`getResource`/`getResourceStack` 都从 `fallbacks` 末尾往前取，**优先级 = 列表靠后 = 先被读到**，所以 `getResourceStack` 返回的顺序是**高优先级在前**。
`TagLoader.load` 按这个顺序累加，遇到 `"replace": true` 时 `list.clear()` —— **清掉的是「优先比自己高」的那些条目**，而**优先级更低的文件在它之后继续 append**。

由此，`terrablender:tags/dimension_type/overworld_regions` 的实际结果是：

| 顺序 | 文件 | 优先级 | 内容 |
|---|---|---|---|
| 1 | `beloong`（mod） | 高 | `replace: true` + `["beloong:disaster"]` |
| 2 | `terrablender`（前置 mod） | 低 | `replace: false` + `["minecraft:overworld"]` |

→ 合并结果 = **`{beloong:disaster}`**（猪排的 `replace` 生效，TB 自己的条目被一并清掉）。详见第 6 节：`TagLoader` 走的是 `listMatchingResourceStacks` → `FallbackResourceManager.listResourceStacks`，那份列表是**升序优先级**（低→高），所以高优先级文件的 `replace: true` 清掉的是**全部更低优先级条目**。因此：

- **主世界从 2026-06-02（38ae579）起就没有 TB 区域注入了**——BWG / VanillaBackport 的群系只在 6 月之前生成的旧区块里还在，新区块不再产；
- 天灾维度反而拿到了 BWG（档 1 的口子，即「假显示」的真源头）。

首版记录里「主世界本就不含 BWG」的推断作废；二次核实的「主世界仍有 BWG」同样作废（见第 6 节）。

**1. `is_disaster` 维持双来源（不改）**
- core：`replace: true` + 71 个 `beloong:disaster_*`（高优先级）；
- 整合包：`kubejs/data/beloong/tags/worldgen/biome/is_disaster.json`（55 个 `biomeswevegone:*`，低优先级、无 replace，追加）。
- tag 语义 = 「算作天灾系的群系」：`beloong:disaster_*` 覆盖天灾维度，`biomeswevegone:*` 覆盖主世界里的 BWG 区域。**两者都保留**，52 个天灾结构因此既能刷在天灾维度（克隆），也能刷在主世界的 BWG 区域。
- 首版曾删除整合包侧文件，导致这 52 个结构在主世界那一栏消失（`该显示的不显示了`），已回滚。

**2. §2.4 TB 退路选定「退役」（仅对天灾维度生效）**
- `data/terrablender/tags/dimension_type/overworld_regions.json` → `{"replace": true, "values": []}`（core，最高优先级）。
- 合并结果变成 `{minecraft:overworld}`：**主世界照旧**，**天灾维度不再被注入 BWG/VB 区域**，维度内只剩 51 个 beloong 克隆（参数表 7593 条）。
- 目的：不再让白名单含 BWG 的 212 个结构（含 BWG 自家 18 个）继续在天灾维度生成；这与「档 2 完全体」一致。
- `CloneParameterListMixin` 一并删除（其保护的共享 ParameterList 场景已不存在）。

**3. 校清单（口径＝白名单 ∩ 维度真实群系）**
- 会显示天灾维度：52（cataclysm 8 / fdbosses 3 / netherman 6 / mss 35）；其中 49 个同时显示主世界（白名单里有 BWG 原 id）。
- 含 BWG 白名单、天灾维度零交集：212。
- 20 个克隆群系未进参数表（映射规则内，暂留）。
- 工具与产物：`~/archive/beloong_dim_audit.py`、`beloong_structure_dimension_audit.{md,html}`。

**4. 待办**
- 整合包其余 BWG 分类 tag 未动：`is_sea`、`is_desert`、`is_snowy`、`is_nether`、`is_end`、`ds_aether_addon/.../cherryskyland`（它们同样是「BWG 区域 + 克隆」双份语义，是否随克隆补条目由 wuhanhao 定）。
- 打包时必须带上重建后的 core jar（0.8.2 之后）。

**5. 罗盘跨维度卡死：根因与拆除（2026-09-11 第二波）**

现象：在天灾维度打开罗盘→关闭→回主世界→再打开罗盘，**卡死**；反方向同样。崩溃栈头部：

```
com.chaosthedude.explorerscompass.util.StructureUtils.getPrettyStructureName(StructureUtils.java:189)
com.chaosthedude.explorerscompass.gui.StructureSearchEntry.render(StructureSearchEntry.java:73)
com.chaosthedude.explorerscompass.gui.StructureSearchList.renderWidget(StructureSearchList.java:63)
```

定位（全部来自 `ExplorersCompass-1.21.1-3.4.0-neoforge.jar` 官方原件，sha1 `9f62af34…` 与 Modrinth 1.21.1-3.4.0 一致，未被改动）：

1. `getPrettyStructureName` 的行号表：`line 189 → offset 0`，即方法第一条指令 `aload_0; invokevirtual ResourceLocation.toString()`。**抛点在方法最开头 ⇒ 入参 `key == null`。**
2. `StructureSearchEntry.render` 行号表：`line 73 → offset 230`，该段唯一调用 `getPrettyStructureName` 的指令在 offset 258，实参是
   `ExplorersCompass.structureKeysToTypeKeys.get(this.structureKey)`（「分组」前缀行，`string.explorerscompass.group`）。
   ⇒ **`structureKeysToTypeKeys` 里查不到这条结构的 key**。
3. 罗盘自身的不变量：`SyncPacket.write` 遍历 `allowedStructureKeys`，每条写 `(key, dims, typeKey, xp)`；`read` 在**同一个循环**里同时填 `allowedStructureKeys` 与 `structureKeysToTypeKeys`。
   ⇒ **客户端 map 的键集合 ≡ 该次同步的 allowed 列表**（不是全注册表）。
4. 屏幕侧：`ExplorersCompassScreen.tick()` 把静态 `allowedStructureKeys` **拷贝**进 `this.allowedStructureKeys` 并用它构建列表项；而渲染时读的是**静态** map。
   ⇒ 只要两次同步的 allowed 集合不同，就会出现「屏幕里是上一次同步的条目 + 静态 map 已换成这一次」→ 查不到 → null → 渲染线程 NPE（游戏卡住/崩溃）。
5. 为什么上游 3.4.0 不炸：原版 `getAllowedStructureKeys` **与维度无关**（返回全量注册表），每次同步键集合都一样，旧条目永远查得到。**是本仓库的维度过滤器让 allowed 集合随维度变化，才打开了这个窗口。**
6. 为什么第一次打开没事、切维度后第二次必炸：第一次打开时客户端静态量尚未同步（列表为空 → 没有条目可渲染），之后的同步两边同源；切换维度后屏幕带着上一维度的条目，新同步一到达就撞上。

处置：**删除 `StructureUtilsMixin`**（连同 `beloong.mixins.json` 注册与 `build.gradle` 的 explorers-compass 可选依赖）。

- 该过滤器（commit `4211264`）当时是为了消灭「天灾专属结构在主世界显示天灾维度」的假显示；但维度栏本来就是罗盘自己算的：`getGeneratingDimensionKeys` = `structure.biomes()` ∩ 各 `ServerLevel` 的 `BiomeSource.possibleBiomes()`，**口径与我们要的完全一致**。假显示的真源头是 TB 注入链（把 BWG 塞进天灾维度、让 `possibleBiomes` 里真的出现了 BWG），该链已由第 2 条退役 —— 过滤器因此既多余，又是卡死的直接原因。
- 保留：`CloneParameterListMixin` 删除、整合包侧 `is_disaster.json` 维持双来源。TB tag 的写法在第 6 节进一步修正为显式 `[minecraft:overworld]`（原先的 `[]` 会把主世界一起摘掉）。

验证：`bash gradlew build --console=plain` → BUILD SUCCESSFUL；产物 `build/libs/beloong-0.8.2.jar`（12,675,971 字节，sha256 `c4a655a2…`）内 `beloong.mixins.json` 无 `explorerscompass` 条目、无 `StructureUtilsMixin` 类（mixins 28 + client 7）。

**6. BWG 村庄无处生成：TB `overworld_regions` 被整体顶掉（2026-09-11 第三波）**

现象：`biomeswevegone` 的 6 个村庄（`village/forgotten`＝遗忘村庄、`salem`、`skyris`、`swamp`、`red_rock`、`pumpkin_patch`）在任何维度都没有可生成群系。它们各自的 `biomes` 白名单是 `#biomeswevegone:has_structure/village_*`，展开后分别是单个/两个 BWG 群系（forgotten → `biomeswevegone:forgotten_forest`），**全部只认 BWG 群系**。

机制（三处一手证据）：

1. **tag 合并顺序**：`TagLoader.load` 走的是 `FileToIdConverter.listMatchingResourceStacks` → `MultiPackResourceManager.listResourceStacks` → `FallbackResourceManager.listResourceStacks`，而后者是 `for (PackEntry e : this.fallbacks)` **正序遍历**（`push` 用 `add` 追加；只有 `getResource`/`getResourceStack` 才是倒序取第一个）⇒ 那份 `List<Resource>` 是**升序优先级**，所以高优先级文件的 `replace: true` 清掉的是**全部更低优先级条目**。第 0 节二次核实的结论（「高优先级在前、replace 只清比自己更高的」）作废——那条错把 `getResourceStack` 的顺序当成了 tag 加载顺序。
2. **实际优先级**：`overworld_regions` 全包只有两个提供者——TB 自己的 `{replace:false, "minecraft:overworld"}` 和 beloong 的 `{replace:true, [...]}`。玩家日志里的 pack 列表（升序）中 `mod/terrablender` 位于 `mod/beloong` **之前**（依赖在前、依赖方在后 ⇒ 后者优先级更高）⇒ 合并结果 = **beloong 的 values 单独生效**：猪排 `38ae579` 之后是 `{beloong:disaster}`，本仓库上一版（`86a0104`）是 `{}`。
3. **消费方**：TB `LevelUtils.getRegionTypeForDimension(Holder<DimensionType>)` = 命中 `NETHER_REGIONS` → NETHER、命中 `OVERWORLD_REGIONS` → OVERWORLD、否则 **null**；`initializeBiomes` 拿到 null 直接 `return` ⇒ **没被列进 tag 的维度类型一律不做区域注入**。于是主世界（dimension type `minecraft:overworld`）自 2026-06-02 起就没有 BWG/VB 区域 ⇒ BWG 群系只在 6 月之前生成的旧区块里存在，新区块不再产 ⇒ BWG 村庄（以及所有白名单只含 BWG 群系的结构）失去生成地。这也解释了罗盘为什么对它们「一个维度都不显示」。

改法：core 的该 tag 显式写 `{"replace": true, "values": ["minecraft:overworld"]}` —— 等于 TB 上游默认，主世界恢复 BWG/VB 注入；`beloong:disaster` 依旧不在列表里，天灾维度继续保持无 BWG（第 2 节目标不受影响）。

注意：旧区块里已生成的 BWG 群系不会回滚，恢复只在**新区块**生效。
