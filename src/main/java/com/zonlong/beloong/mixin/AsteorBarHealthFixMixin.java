package com.zonlong.beloong.mixin;

import by.dragonsurvivalteam.dragonsurvival.common.capability.DragonStateProvider;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ClientPacketListener;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.network.protocol.game.ClientboundRespawnPacket;
import net.minecraft.network.protocol.game.ClientboundSetHealthPacket;
import net.minecraft.network.protocol.game.ClientboundUpdateAttributesPacket;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.player.Player;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.List;

/**
 * 保留原血量修复类与配置登记，在一个类中处理跨维度血量恢复和成长回血数字。
 *
 * <p>跨维度时，SetHealth 包早于最大血量属性包会经 hurtTo/setHealth 被旧上限钳制。
 * 属性同步后仍使用 setHealth 恢复，但值取自当前玩家最新服务器包，不再从旧玩家或
 * HUD 帧数推断。较新伤害/死亡包和玩家替换会撤销旧恢复值，服务器结算不受影响。</p>
 *
 * <p>同一 Mixin 另以字符串目标兼容可选 Health Bars，仅替换回血数字 getter 的返回值，
 * 不依赖其私有字段，也不改血条动画。成长导致的同比例血量变化在两个客户端 tick 内
 * 扣除，普通伤害与治疗保留。状态分别存于连接和 HealthTracker 实例，互不共享。</p>
 *
 * <p>这是一个多目标 Mixin：每个注入只匹配所属目标的方法，require = 0 用于跳过
 * 其他目标及可选模组的缺席，不保证未来方法签名仍兼容。NeoForge 1.21.1 使用 Mojang
 * 方法名，故 remap = false；实际核对基线为 NeoForge 21.1.248、DS 2.0.71、Health Bars 21.1.0。</p>
 */
@Pseudo
@Mixin(value = ClientPacketListener.class, targets = "fuzs.healthbars.client.helper.HealthTracker", remap = false)
public abstract class AsteorBarHealthFixMixin {

    @Unique
    private Object beloong$pendingPlayer;

    @Unique
    private float beloong$pendingHealth = Float.NaN;

    @Unique
    private Object beloong$trackedEntity;

    @Unique
    private Object beloong$trackedLevel;

    @Unique
    private boolean beloong$filterNumbers;

    @Unique
    private float beloong$filteredDelta;

    @Unique
    private ArrayDeque<Float> beloong$ready;

    @Unique
    private List<Float> beloong$rawChanges;

    @Unique
    private boolean beloong$initialized;

    @Unique
    private boolean beloong$pendingGrowth;

    @Unique
    private boolean beloong$capacityChanged;

    @Unique
    private boolean beloong$growthChanged;

    @Unique
    private int beloong$lastTick;

    @Unique
    private int beloong$firstChangeTick;

    @Unique
    private float beloong$lastHealth;

    @Unique
    private float beloong$lastMaxHealth;

    @Unique
    private double beloong$lastGrowth;

    @Unique
    private float beloong$startHealth;

    @Unique
    private float beloong$startMaxHealth;

    // TAIL 已经过原版包线程调度与血量钳制，只在客户端游戏线程记录原始值。
    @Inject(
            method = "handleSetHealth(Lnet/minecraft/network/protocol/game/ClientboundSetHealthPacket;)V",
            at = @At("TAIL"), require = 0
    )
    private void beloong$rememberHealth(ClientboundSetHealthPacket packet, CallbackInfo ci) {
        LocalPlayer player = Minecraft.getInstance().player;
        beloong$receiveHealth(player, packet.getHealth(), player == null ? 0 : player.getMaxHealth());
    }

    @Inject(
            method = "handleUpdateAttributes(Lnet/minecraft/network/protocol/game/ClientboundUpdateAttributesPacket;)V",
            at = @At("TAIL"), require = 0
    )
    private void beloong$restoreHealth(ClientboundUpdateAttributesPacket packet, CallbackInfo ci) {
        Minecraft minecraft = Minecraft.getInstance();
        LocalPlayer player = minecraft.player;
        if (player == null || minecraft.level == null
                || minecraft.level.getEntity(packet.getEntityId()) != player
                || packet.getValues().stream().noneMatch(snapshot -> snapshot.attribute().equals(Attributes.MAX_HEALTH))) {
            return;
        }
        float health = beloong$takeHealth(player, player.getMaxHealth());
        if (Float.isFinite(health)) {
            player.setHealth(health);
        }
    }

    @Inject(
            method = "handleRespawn(Lnet/minecraft/network/protocol/game/ClientboundRespawnPacket;)V",
            at = @At("TAIL"), require = 0
    )
    private void beloong$resetOnRespawn(ClientboundRespawnPacket packet, CallbackInfo ci) {
        beloong$resetHealth();
    }

    @Unique
    protected void beloong$resetHealth() {
        beloong$pendingPlayer = null;
        beloong$pendingHealth = Float.NaN;
    }

    @Unique
    protected void beloong$receiveHealth(Object player, float health, float maxHealth) {
        beloong$resetHealth();
        if (player != null && Float.isFinite(health) && Float.isFinite(maxHealth)
                && maxHealth > 0 && health > maxHealth) {
            beloong$pendingPlayer = player;
            beloong$pendingHealth = health;
        }
    }

    @Unique
    protected float beloong$takeHealth(Object player, float maxHealth) {
        if (beloong$pendingPlayer != player || !Float.isFinite(maxHealth) || maxHealth <= 0) {
            beloong$resetHealth();
            return Float.NaN;
        }
        if (Float.isNaN(beloong$pendingHealth) || beloong$pendingHealth > maxHealth) {
            return Float.NaN;
        }
        float health = beloong$pendingHealth;
        beloong$resetHealth();
        return health;
    }

    @Inject(
            method = "tick(Lnet/minecraft/world/entity/LivingEntity;)V",
            at = @At("TAIL"), require = 0
    )
    private void beloong$sampleNumbers(LivingEntity entity, CallbackInfo ci) {
        beloong$filterNumbers = entity.level().isClientSide()
                && entity instanceof Player player && DragonStateProvider.isDragon(player);
        if (!beloong$filterNumbers) {
            beloong$resetGrowth();
            beloong$trackedEntity = null;
            beloong$trackedLevel = null;
            return;
        }
        if (beloong$trackedEntity != entity || beloong$trackedLevel != entity.level()) {
            beloong$resetGrowth();
            beloong$trackedEntity = entity;
            beloong$trackedLevel = entity.level();
        }
        beloong$filteredDelta = beloong$sampleGrowth(entity.tickCount, entity.getHealth(), entity.getMaxHealth(),
                DragonStateProvider.getData((Player) entity).getGrowth());
    }

    // 使用公开 getter，避免多目标 Mixin 的 @Shadow 要求每个目标都有同名字段。
    @Inject(method = "getLastHealthDelta()I", at = @At("HEAD"), cancellable = true, require = 0)
    private void beloong$filterNumber(CallbackInfoReturnable<Integer> cir) {
        if (beloong$filterNumbers) {
            cir.setReturnValue((int) Math.ceil(Math.abs(beloong$filteredDelta)) * (int) Math.signum(beloong$filteredDelta));
        }
    }

    @Unique
    protected void beloong$resetGrowth() {
        beloong$initialized = false;
        beloong$pendingGrowth = false;
        beloong$filteredDelta = 0;
        if (beloong$ready != null) {
            beloong$ready.clear();
            beloong$rawChanges.clear();
        }
    }

    /** 相邻包使用固定两 tick 窗口；连续成长不能一直推迟输出。 */
    @Unique
    protected float beloong$sampleGrowth(int tick, float health, float maxHealth, double growth) {
        if (!Float.isFinite(health) || !Float.isFinite(maxHealth) || !Double.isFinite(growth) || maxHealth <= 0) {
            beloong$resetGrowth();
            return 0;
        }
        health = Math.clamp(health, 0, maxHealth);
        if (!beloong$initialized || tick < beloong$lastTick) {
            beloong$resetGrowth();
            if (beloong$ready == null) {
                beloong$ready = new ArrayDeque<>();
                beloong$rawChanges = new ArrayList<>(3);
            }
            beloong$initialized = true;
            beloong$lastTick = tick;
            beloong$lastHealth = health;
            beloong$lastMaxHealth = maxHealth;
            beloong$lastGrowth = growth;
            return 0;
        }
        if (tick == beloong$lastTick) {
            return 0;
        }
        if (!beloong$pendingGrowth && (health != beloong$lastHealth || maxHealth != beloong$lastMaxHealth
                || growth != beloong$lastGrowth)) {
            beloong$pendingGrowth = true;
            beloong$capacityChanged = false;
            beloong$growthChanged = false;
            beloong$firstChangeTick = tick;
            beloong$startHealth = beloong$lastHealth;
            beloong$startMaxHealth = beloong$lastMaxHealth;
        }
        if (beloong$pendingGrowth) {
            beloong$capacityChanged |= maxHealth != beloong$lastMaxHealth;
            beloong$growthChanged |= growth != beloong$lastGrowth;
            if (health != beloong$lastHealth) {
                beloong$rawChanges.add(health - beloong$lastHealth);
            }
            if (tick - beloong$firstChangeTick >= 2 || health == 0) {
                float tolerance = Math.max(1.0e-6F,
                        4 * Math.max(Math.ulp(beloong$startHealth), Math.ulp(health)));
                if (beloong$capacityChanged && beloong$growthChanged) {
                    double expectedHealth = (double) beloong$startHealth * maxHealth / beloong$startMaxHealth;
                    beloong$enqueueDelta((float) (health - expectedHealth), tolerance);
                } else {
                    // 普通治疗后紧接伤害不能因净变化为零而相互抵消。
                    for (float change : beloong$rawChanges) {
                        beloong$enqueueDelta(change, tolerance);
                    }
                }
                beloong$pendingGrowth = false;
                beloong$rawChanges.clear();
            }
        }
        beloong$lastTick = tick;
        beloong$lastHealth = health;
        beloong$lastMaxHealth = maxHealth;
        beloong$lastGrowth = growth;
        return beloong$ready.isEmpty() ? 0 : beloong$ready.removeFirst();
    }

    @Unique
    private void beloong$enqueueDelta(float delta, float tolerance) {
        if (Math.abs(delta) <= tolerance) {
            return;
        }
        float nearestInteger = (float) Math.rint(delta);
        if (Math.abs(delta - nearestInteger) <= tolerance) {
            delta = nearestInteger;
        }
        beloong$ready.addLast(delta);
    }
}
