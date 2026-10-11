package com.zonlong.beloong.client.health;

import com.zonlong.beloong.mixin.AsteorBarHealthFixMixin;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class PendingHealthUpdateTest {
    private static final class PendingHealthUpdate extends AsteorBarHealthFixMixin {
        void reset() {
            beloong$resetHealth();
        }

        void receive(Object player, float health, float maxHealth) {
            beloong$receiveHealth(player, health, maxHealth);
        }

        float takeReady(Object player, float maxHealth) {
            return beloong$takeHealth(player, maxHealth);
        }
    }

    @ParameterizedTest
    @ValueSource(floats = {40, 80, 100})
    void healthBeforeAttributesRecoversExactServerValue(float health) {
        var client = new Client();
        client.healthPacket(health);
        assertEquals(20, client.health);
        client.attributes(100);
        assertEquals(health, client.health);
    }

    @Test
    void attributesBeforeHealthKeepsNormalVanillaBehavior() {
        var client = new Client();
        client.attributes(100);
        client.healthPacket(80);
        assertEquals(80, client.health);
        assertTrue(Float.isNaN(client.pending.takeReady(client.player, 100)));
    }

    @Test
    void latestDamagePacketReplacesEarlierClampedHealth() {
        var client = new Client();
        client.healthPacket(100);
        client.healthPacket(45);
        client.attributes(100);
        assertEquals(45, client.health);
    }

    @ParameterizedTest
    @ValueSource(floats = {0, 5, 20})
    void newerUnclampedHealthCancelsRestoration(float health) {
        var client = new Client();
        client.healthPacket(100);
        client.healthPacket(health);
        client.attributes(100);
        assertEquals(health, client.health);
    }

    @Test
    void latestHealingPacketReplacesEarlierClampedHealth() {
        var client = new Client();
        client.healthPacket(45);
        client.healthPacket(80);
        client.attributes(100);
        assertEquals(80, client.health);
    }

    @Test
    void incompleteAttributesDoNotConsumeThePendingValue() {
        var client = new Client();
        client.healthPacket(80);
        client.attributes(40);
        assertEquals(20, client.health);
        client.attributes(100);
        assertEquals(80, client.health);
    }

    @Test
    void interveningClientGrowthCalculationDoesNotReplaceServerValue() {
        var client = new Client();
        client.healthPacket(45);
        client.health = 100; // Client growth modifiers rescaled the clamped health.
        client.attributes(100);
        assertEquals(45, client.health);
    }

    @Test
    void correctionIsConsumedAndCannotUndoLaterHealthChanges() {
        var client = new Client();
        client.healthPacket(80);
        client.attributes(100);
        client.health = 70;
        client.attributes(110);
        assertEquals(70, client.health);
    }

    @Test
    void replacementPlayerCannotReceiveOldPlayersHealth() {
        var client = new Client();
        client.healthPacket(80);
        client.player = new Object(); // Even if the entity ID is reused.
        client.health = 10;
        client.attributes(100);
        assertEquals(10, client.health);
    }

    @Test
    void respawnOrDimensionResetCancelsPendingHealth() {
        var client = new Client();
        client.healthPacket(80);
        client.pending.reset();
        client.health = 10;
        client.attributes(100);
        assertEquals(10, client.health);
    }

    @ParameterizedTest
    @ValueSource(floats = {Float.NaN, Float.POSITIVE_INFINITY, Float.NEGATIVE_INFINITY})
    void invalidHealthPacketCannotLeaveAnOldCorrection(float health) {
        var pending = new PendingHealthUpdate();
        Object player = new Object();
        pending.receive(player, 80, 20);
        pending.receive(player, health, 20);
        assertTrue(Float.isNaN(pending.takeReady(player, 100)));
    }

    private static final class Client {
        final PendingHealthUpdate pending = new PendingHealthUpdate();
        Object player = new Object();
        float maxHealth = 20;
        float health = 20;

        void healthPacket(float value) {
            health = Math.clamp(value, 0, maxHealth); // LivingEntity.setHealth
            pending.receive(player, value, maxHealth);
        }

        void attributes(float value) {
            maxHealth = value;
            float correction = pending.takeReady(player, maxHealth);
            if (Float.isFinite(correction)) {
                health = Math.clamp(correction, 0, maxHealth);
            }
        }
    }
}
