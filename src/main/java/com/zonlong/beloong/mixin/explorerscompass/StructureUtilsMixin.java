package com.zonlong.beloong.mixin.explorerscompass;

import com.chaosthedude.explorerscompass.util.StructureUtils;
import net.minecraft.core.Holder;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.biome.Biome;
import net.minecraft.world.level.levelgen.structure.Structure;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;

/**
 * 为探险罗盘（Explorer's Compass）的「可搜索结构列表」补齐维度可生成性过滤。
 *
 * <p>原版 {@link StructureUtils#getAllowedStructureKeys} 只遍历整个 structure 注册表并施加
 * 配置黑名单与 hidden tag，<b>不做任何维度校验</b>。因此在天灾维度专属结构（其
 * {@code structure.biomes} 全部是 {@code #beloong:is_disaster} 系列群系、主世界并不存在）上，
 * 主世界打开罗盘时这些结构会被一并列出来，玩家选择后搜索必然一无所获——列表「假显示」。</p>
 *
 * <p>本 mixin 在方法返回时按维度过滤：仅保留 {@code structure.biomes()} 与当前维度
 * {@code BiomeSource.possibleBiomes()} 存在交集的结构，无交集者从列表中剔除。</p>
 */
@Pseudo
@Mixin(value = StructureUtils.class, remap = false)
public class StructureUtilsMixin {

    /**
     * 在 {@code getAllowedStructureKeys} 返回前过滤掉「当前维度根本无法生成」的结构。
     */
    @Inject(method = "getAllowedStructureKeys", at = @At("RETURN"), cancellable = true, remap = false)
    private static void beloong$filterByDimension(
            ServerLevel level,
            CallbackInfoReturnable<List<ResourceLocation>> cir
    ) {
        List<ResourceLocation> allowed = cir.getReturnValue();
        if (allowed == null || allowed.isEmpty()) {
            return;
        }

        // 与原方法同源的注册表：直接复用被拦截方法的 level 参数反查 Structure 实例
        Registry<Structure> structureRegistry = level.registryAccess().registryOrThrow(Registries.STRUCTURE);
        // 当前维度实际可用的群系集合
        Set<Holder<Biome>> possibleBiomes = level.getChunkSource().getGenerator().getBiomeSource().possibleBiomes();

        List<ResourceLocation> filtered = new ArrayList<>(allowed.size());
        for (ResourceLocation key : allowed) {
            Structure structure = structureRegistry.get(key);
            // 查不到结构时保守保留原条目（不因查表失败而误删）
            if (structure == null) {
                filtered.add(key);
                continue;
            }
            // 结构与当前维度群系有交集才可搜索；天灾专属结构在主世界无匹配群系 → 剔除
            if (structure.biomes().stream().anyMatch(possibleBiomes::contains)) {
                filtered.add(key);
            }
        }
        cir.setReturnValue(filtered);
    }
}
