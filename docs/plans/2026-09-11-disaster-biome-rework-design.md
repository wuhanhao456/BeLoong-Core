# 天灾维度群系重制设计（去原版地表群系 + 探险罗盘维度过滤）

> 状态：**设计稿，待审查**
> 日期：2026-09-11
> 决策已确认（wuhanhao，2026-09-11）：
> 1. 保留洞穴/地形 → 采用新命名空间方案（不删地形引擎，只换群系构成）
> 2. 探险罗盘假结构 → 方案 2：beloong core mixin 维度过滤
> 3. 地表群系用「像对像」映射；水域和洞穴尽量也换；提交必须落在 wuhanhao456 fork

---

## 一、机制背景（1.21.1 事实，已核实）

- **地形与群系是两套系统**：地形起伏、洞穴、矿物雕刻由 `noise_settings` 的 noise_router/density_function 决定；`multi_noise` biome source 只决定气候点 → 群系映射（palette + 群系自带表面规则）。换群系不丢洞穴。
- **1.21.1 的关键变化**：原版 `multi_noise_biome_source_parameter_list/overworld.json` **只含 `{"preset":"minecraft:overworld"}`**（指向代码内注册表，已下载原版 1.21.1 client.jar 核实——datapack 与 mcmeta data-json 分支均如此）。真正的参数条目在 `OverworldMultiNoiseBiomeSourceParameterList` 代码 bootstrap 里，**没有任何 datapack JSON 载体**。因此自定义 preset 必须内联完整 parameterList，条目数据要在实现阶段从运行时 dump / mapped jar 提取，不能从原版数据包复制（此前设计假设错误，已修正）。
- **BWG 侧事实**：`Oh-The-Biomes-Weve-Gone-NeoForge-2.6.0.jar` 的 `data/biomeswevegone/worldgen/biome/` 共 **55 个群系 JSON**，与整合包 `kubejs/data/beloong/tags/worldgen/biome/is_disaster.json` 的 55 条完全一致。**其中没有洞穴群系，也没有纯海洋群系**（岸线/湿地有：rainbow_beach、dacite_shore、dead_sea、white_mangrove_marshes、bayou 等）。
- **TerraBlender 注入**：BWG 用 `RegionType.OVERWORLD` 注册 region（`BWGTerraBlenderRegion`，`Regions.register`），TB 的 `LevelUtils.initializeBiomes` 会对**所有** `multi_noise` biome source 调 `IExtendedParameterList.initializeForTerraBlender`，按维度 type tag 决定注入。region size/weight 由 `config/terrablender.toml` 控制（overworld_region_size=3，vanilla_overworld_region_weight=10）。

## 二、问题 A：天灾维度去原版地表群系

### 2.1 现状

`data/beloong/dimension/disaster.json`：`settings: minecraft:overworld` + `biome_source.preset: minecraft:overworld`。结果：原版地表群系 + TB 注入的 BWG 群系混合。

### 2.2 目标构成

| 层 | 改动 | 理由 |
|---|---|---|
| 地表陆生群系 | 原版 → BWG（像对像映射，约 30 条） | 去"原版地形感" |
| 水域 | **海/河/深水域保留原版**（BWG 2.6.0 无纯海洋群系，如实说明）；**岸线/滩涂/湿地换 BWG**（rainbow_beach、dacite_shore、dead_sea、white_mangrove_marshes、bayou、cypress_wetlands） | 用户要求"水域也换"；BWG 能换的换，换不了的保留并在文档标注 |
| 洞穴 | **保留原版**（dripstone_caves / lush_caves / deep_dark + cheese/squirm/worm 全套洞穴密度函数） | BWG 2.6.0 无洞穴群系；保留原版正是"洞穴必须还在"的保证 |

### 2.3 新增文件（全部 beloong 命名空间）

1. `data/beloong/multi_noise_biome_source_parameter_list/disaster.json`
   - 内联完整 `parameters` 列表（实现阶段从 1.21.1 运行时或映射 jar 提取原版条目，**提取后校验条目数与区间连续性**）
   - 气候区间（temperature/humidity/continentalness/erosion/depth/weirdness/offset）**原样保留**——这是洞穴与地形分布逻辑的载体
   - 仅替换地表条目的 `biome` 值；地下与水域条目保留 `minecraft:*`
2. `data/beloong/worldgen/noise_settings/disaster.json`
   - 原版 `noise_settings/overworld.json` 的完整拷贝（sea_level 63、surface_rule、noise_router、spawn_target 全保留；aquifers/ore_veins 开启照旧）
   - 内部 `minecraft:` 资源引用（density_function/noise/结构等）**按 ID 原样引用原版**，不复制依赖文件
3. `data/beloong/dimension/disaster.json`
   - `settings` → `beloong:disaster`；`biome_source.preset` → `beloong:disaster`

### 2.4 映射表（像对像，完整表见实现 PR）

设计原则：气候等价（温度/湿度档位对应），优先选同气候带的 BWG 群系。示例方向（最终以逐条评审表为准）：

| 原版 | BWG |
|---|---|
| plains | prairie |
| savanna | baobab_savanna / allium_shrubland |
| jungle | tropical_rainforest / fragment_jungle |
| desert | windswept_desert / mojave_desert |
| badlands | rugged_badlands / sierra_badlands |
| snowy_plains / snowy_taiga | crimson_tundra / shattered_glacier / frosted_taiga |
| taiga | aspen_boreal /zelkova_forest |
| beach / stony_shore | rainbow_beach / dacite_shore |
| swamp | cypress_wetlands / white_mangrove_marshes / pale_bog |
| 有林高山 | howling_peaks / skyris_vale |
| （其余原版地表群系逐条入表） | |

### 2.5 联动与风险

- **TerraBlender 双来源**：TB 仍按 region 注入 BWG 大区块 + preset 内散点同在，构成一致（全是 BWG），无空洞风险。需实测确认自定义 preset 下 TB 的 `IExtendedParameterList.initializeForTerraBlender` 正常追加（`Initialized TerraBlender biomes for level stem` 日志 + 区块 NBT 抽样）。
- **CloneParameterListMixin 变为冗余但无害**（两维度 preset 不再共享实例），保留不动，不删——防回退。
- **`beloong:is_disaster` tag**：已是 BWG 全集 55 条，无需改。
- **原版结构退场**：村庄/前哨站/大型迷宫等依赖原版地表群系的结构将不再出现在天灾（其 `biomes` 引用原版群系或 `has_structure` 原版 tag）。预期内变化，写入 PR 描述；`disaster_set`/`disaster_set_ground`（salt 20260604/20260829）引用的结构若依赖原版群系需逐一核对——**这是阶段 1 实测的重点清单**。
- **旧存档**：已生成天灾区块不重生成；验证只看新区块或重置维度。
- **BWG 禁用群系**：BWG 配置禁用的群系在 preset 散点与 TB 注入两侧都不会出现，与现有主世界行为一致。

### 2.6 验收标准

新区块抽样（复用总设计文档 4.5 的区块 NBT palette 抽样法）：
- 地表群系 `minecraft:*` 命中 = 0（允许水域例外项）
- `dripstone_caves` / `lush_caves` / `deep_dark` 在地下抽样中可见
- TB 日志正常初始化天灾维度
- 罗盘在天灾维度内对 cataclysm/fdbosses 竞技场搜索实际命中（阶段 2 合并验证）

## 三、问题 B：探险罗盘假结构（core mixin 维度过滤）

### 3.1 根因（ExplorersCompass 3.4.0 反编译核实）

- `StructureUtils.getAllowedStructureKeys()` 遍历**当前维度整个 structure 注册表**（registry 全维度共享），仅应用 config `structureBlacklist` 与 `hidden` tag，**不做当前维度可生成性校验**。
- 罗盘自带 `getGeneratingDimensionKeys()`（`structure.biomes()` vs 各维度 `BiomeSource.possibleBiomes()` 交集判断），仅用于 GUI 分组展示，搜索入口不消费。
- 天灾结构（cataclysm 8 竞技场 / fdbosses 3 竞技场 / mss、netherman 等 disaster_set 成员）`biomes` 全为 `#beloong:is_disaster`（纯 BWG），主世界是纯净原版群系 → 主世界列表照列、搜索必空。

### 3.2 实现（BeLoong-Core）

- 新增 `mixin/explorerscompass/StructureUtilsMixin`：
  - `@Pseudo` + `remap = false`（沿用项目对 TerraBlender 的既有先例），罗盘缺席时静默失效
  - `@Inject(method = "getAllowedStructureKeys", at = @At("RETURN"), cancellable)`：对返回列表按「`structure.biomes()` ∩ 当前维度 `possibleBiomes()` ≠ ∅」过滤（与罗盘自身维度判定同逻辑），cancellable 写回过滤后列表
  - 列表入口过滤一次，GUI 与搜索行为同时修复
- `beloong.mixins.json` 注册；`build.gradle` 加 ExplorersCompass EXTERNAL / 仓库依赖（仅编译期）。
- 附带收益：下界/末地专属结构从主世界列表消失（同类假结构一并修复）。

### 3.3 验收标准

- 主世界罗盘列表：无 `#beloong:is_disaster` 系结构（附全名单核对）
- 天灾维度内：cataclysm/fdbosses 竞技场在列且搜索可实际定位
- 罗盘模组缺席的服务器：mixin 不加载、无报错

## 四、阶段与提交

| 阶段 | 内容 | 交付 |
|---|---|---|
| 0 | 参数条目提取（运行时 dump 或映射 jar），映射表逐条成文 | 提取脚本 + 校验报告 |
| 1 | 阶段二全部数据文件 + 实测（重点：原版结构退场清单核对） | BeLoong-Core 提交 |
| 2 | StructureUtilsMixin + 回归 | 同一或后续提交 |
| 收尾 | 更新 `docs/天灾维度总设计.md`「现行实现」标注 | 同 PR |

- **提交目标**：`origin = https://github.com/wuhanhao456/BeLoong-Core.git`（fork，已核实 gh 登录账号 wuhanhao456、本地 HEAD `585f823` 与 fork 一致）。全部提交推至该 fork 的 `master`，不触 PorkChop-ZLG 上游。
- 存档仓库纪律照旧：原版 + 本仓库 = 完美复现；不用 CI；docs 随源码走。

## 五、待审查点

1. 映射表风格（2.4 是方向示例，完整逐条表在实现阶段成文供审）
2. 水域保留原版海/河（BWG 无纯海洋群系）是否接受；若要彻底无原版水域，需引入第三方海洋群系或自写，成本另计
3. 天灾维度内原版结构退场是预期行为（村庄等消失）——确认接受与否，涉及是否在 preset 里为这些结构保留个别原版群系点位
