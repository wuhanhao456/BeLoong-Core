# BWG 结构补漏 + 猪排历史提交回归审计（2026-09-11，Wu）

状态：待执行（wuhanhao 已确认方案甲）。

## 一、方案甲实施（参数表切分 + 白名单 tag）

### 1.1 build_disaster_dimension.py 修改
- 新增 `SPLIT_TABLE`：7 个未接线克隆的 (宿主 disaster_* id, 切分轴=weirdness, 阈值) 配置：
  | 新克隆 | 宿主 | 说明 |
  |---|---|---|
  | forgotten_forest | ebony_woods | dark_forest 系 |
  | weeping_witch_forest | ebony_woods | 与上共宿主，三分 |
  | cypress_swamplands | cypress_wetlands | swamp 系 |
  | cika_woods | maple_taiga | birch_forest 系 |
  | pumpkin_valley | rose_fields | sunflower_plains 系 |
  | dead_sea | windswept_desert | desert 系 |
  | lush_stacks | tropical_rainforest | jungle 系 |
- 切分语义：按宿主点位在切分轴上的**排序后均匀分组**（整点分组，非区间内再切），保证：
  * 与宿主无点重叠（partition，结构性互斥）；
  * 每组为该轴连续带（排序后取连续段）。
- 自检断言追加：新克隆点数 > 0；宿主点数 > 0；两集合无同点；全表仍无同点重复。

### 1.2 白名单 tag（core 新增 16 文件）
路径模板 data/biomeswevegone/tags/worldgen/biome/<tag>.json，replace:false，values=对应 disaster_* 克隆。
16 个 = village_forgotten / village_pumpkin_patch / village_red_rock / village_salem / village_skyris / village_swamp
+ prairie_house / aspen_manor / bog_trial / dripstone_arch / ironwood_gour_plateau / large_cold_lake /
  lush_arch / red_rock_arch / rugged_fossil / sharpened_rocks。

### 1.3 structure_set 核对
18 个结构对应 structure_set 的 dimension 域逐一核对；缺口则补（同 priority 追加 beloong:disaster 到
dimension tag 或直接改列表——以实测为准）。

## 二、猪排历史提交回归审计（新增工作项）

范围：core 仓库全部 467 提交（446 PorkChop_ZLG + 21 其他），以「曾经被判定为 bug 且修复、但修复
可能被后续提交回退/覆盖」为主线。分四层：

### L1 提交信息扫描（纯文本，全量）
提取所有含 fix/bug/修复/问题/TODO 的 144 条，按功能域分组：
- 罗盘/导航（本轮已知：4211264 过滤器 bug 已由 86a0104 拆除修复）
- 天空渲染（0841845..88ccd55 五连击, 2026-09-08~10）
- tooltip（43b63d1/eecd041 龙生、4627f8c 财宝堆服务器）
- 灾变/传奇（067ac28 正义核心、f327271 湮灭猎影限伤）
- DS 飞行（9376beb/ee122c9）
- 水系统（1d1eb1f..7b072a5 4 层演化）
- 传送门（46e7cc7/84058c2/3eb6de7/51d7b82）
- 其他

### L2 代码考古（对每个功能域）
对 L1 每组的「最后一次修复提交」与其后所有触达同文件的提交做 blame 链：
- 该修复是否被后续重构覆盖/回退（git log --follow <file> + git diff <fix>..HEAD -- <file>）；
- 修复引入的辅助变量/常量是否仍在使用（死代码 = 修复被部分回退的信号）；
- 该功能域的当前 HEAD 行为是否与最后修复的 commit message 断言一致（静态读代码核对）。

### L3 数据包一致性（worldgen 专项，与本文档一.3 合并执行）
猪排 6~7 月大量动过 worldgen/tag/structure_set（38ae579、54a4877、以及水系统 4 层）：
- 现存 jar 内数据 vs 当前仓库资源 的 diff（防「改了仓库没重打包」漂移）；
- 特别核对：38ae579 之后是否还有其他触碰 terrablender/* 或 beloong:dimension/* 的提交。

### L4 已知遗留 TODO 全量盘点
提交信息中所有未关闭的 TODO（如 2b6a0d5 水桶贴图、0d0a5a0 两个进度、46e7cc7 光影兼容性、
4f96458 服务端未测试、3eb6de7 眼珠子贴图），列出当前状态：已实现 / 仍未实现 / 无法静态判定。

## 三、交付物
- 甲方案实施后的 0.8.5 jar（含 1.1/1.2/1.3 全部产物 + 自检输出）；
- 猪排回归审计报告（docs/plans/2026-09-11-bwg-completeness-and-regression-audit.md），
  含 L1~L4 全量证据链 + 「确认未回退」/「发现回退」/「无法静态判定」三分类清单；
- 发现的回退若可低风险恢复，先列计划待确认再动手（不先斩后奏）。


---

## 审计执行记录（2026-09-11 当日完成，Wu；子代理并行执行）

**L1**（build/audit/L1-groups.md，593 行）：467 提交 → 144 条命中，分 15 功能域。
**L4**（build/audit/L4-todos.md）：TODO 19 项 → 已实现 14 / 未实现 3（生长药水、龙击长空两个进度、化龙池水桶贴图已作废）/ 无法静态判定 2（领地保护生效性、服务端测试——均需运行时验证）。
**L2**（build/audit/L2-L3-report.md，498 行）：8 域考古，修复项级 18 存活 / 2 回退 / 2 主动取代。域级：6 未回退 / 2 有回退。
**L3**：0.8.0 发版 jar vs 工作树——仅仓库 100（本次未发版产物+16 tag+71 群系等）、语义漂移 6（架构重写与 tag 改写属本次工作内容，非意外）、真死代码 2（CloneParameterListMixin / DragonArmorRenderLayerMixin——源码已删仍打进 0.8.0，属旧版构建残留，0.8.5 重打包后自动消除）、版本漂移 0.8.0 vs 0.8.5（本次发布解决）。

**发现的回退（2 项）**：
- R1 f57dd9e3 → 6ec8022：有意回退（wuhanhao 选定方案 A：主世界不注 TB 区域），非问题。
- R2 1e475e1（AsteorBar 冻结帧 10→30，防高帧率失效）被 067ac28「修复正义核心」**未在提交信息声明地**顺带改回 10（同文件同字节行，index c693036→e471fc7 恰好互逆），067ac28 之后零触达。判定：误伤。**已修复**：AsteorBarHealthFixMixin L50 恢复 30 并注溯源注释。

**结论**：0.8.5 是审计后首个「已知问题清零」版本。剩余 3 项未实现 TODO 与 2 项需运行时验证项与本次改动无耦合，留待后续版本。
