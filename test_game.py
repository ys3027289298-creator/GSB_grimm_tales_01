"""Regression tests for the Grimm-Tales state machine.

Covers the five coupled chains: story gating, player attributes, battle
resolution, save/load and the death state.
"""
import contextlib
import io
import json
import os
import tempfile
import unittest
from unittest import mock

import code as game_mod


def scripted_inputs(*values):
    """Feed a fixed script into the game's input gate."""
    answers = iter(values)

    def fake_input(prompt=""):
        try:
            return next(answers)
        except StopIteration:
            raise StopIteration("input script exhausted")

    return fake_input


def queued_randint(*values):
    """Deterministic random.randint: consume the queue, then fall back to low."""
    queue = list(values)

    def fake_randint(a, b):
        if queue:
            return queue.pop(0)
        return a

    return fake_randint


class FakeRandom:
    def __init__(self, randint=None, randrange=None):
        self._randint = randint or (lambda a, b: a)
        self._randrange = randrange or (lambda a, b: a)

    def randint(self, a, b):
        return self._randint(a, b)

    def randrange(self, a, b):
        return self._randrange(a, b)


class GameTestCase(unittest.TestCase):
    def setUp(self):
        self.game = game_mod.new_game()
        game_mod.questlist = ['1. slay 10 Bandits\n', '2. slay 10 undead soldiers\n']
        self._stdout = io.StringIO()
        self._redirect = contextlib.redirect_stdout(self._stdout)
        self._redirect.__enter__()

    def tearDown(self):
        self._redirect.__exit__(None, None, None)

    def use_inputs(self, *values):
        patcher = mock.patch.object(game_mod, "_real_input", scripted_inputs(*values))
        patcher.start()
        self.addCleanup(patcher.stop)

    def use_random(self, randint=None, randrange=None):
        patcher = mock.patch.object(game_mod, "random", FakeRandom(randint, randrange))
        patcher.start()
        self.addCleanup(patcher.stop)

    def suppress_script_end(self):
        return contextlib.suppress(StopIteration)


class TestAttributeBounds(GameTestCase):
    """Chain: attributes -> battle resolution."""

    def test_fresh_hero_satisfies_invariants(self):
        self.assertTrue(self.game.validate())
        self.assertEqual(self.game.str + self.game.res + self.game.dex,
                         game_mod.gconfig.points)

    def test_out_of_range_attributes_are_rejected_at_the_boundary(self):
        self.game.dex = 999
        self.assertFalse(self.game.stats_valid())
        with self.assertRaises(game_mod.GameError):
            self.game.validate()

    def test_battle_probabilities_are_clamped(self):
        # even if an out-of-range dex slips through, rolls stay inside 0..100
        self.game.dex = 999
        self.use_random(randint=lambda a, b: b)  # worst-case roll
        self.assertEqual(game_mod.calc_enemy_dmg(30), 0)  # 100% evade cap
        self.game.player_dmg = 10
        self.assertGreater(game_mod.get_hero_dmg(), 0)    # 100% hit cap

    def test_damage_uses_exponent_not_xor(self):
        self.game.player_level = 2
        self.game.str = 1
        self.game.player_dmg = 0
        self.game.equipped_weapon = []
        self.use_random(randint=lambda a, b: 1)  # always hit
        # 2 ** 2 == 4, the old `2 ^ 2` (xor) produced 0
        self.assertEqual(game_mod.get_hero_dmg(), 4 + 5)

    def test_enemy_level_bands_are_exclusive(self):
        self.use_random()
        game_mod.randoms('sea scene 3')
        self.assertTrue(17 <= self.game.enemy_level <= 20)
        game_mod.randoms('desert trial 2')
        self.assertTrue(5 <= self.game.enemy_level <= 7)
        game_mod.randoms('graveyard')
        self.assertTrue(1 <= self.game.enemy_level <= 5)

    def test_level_up_stops_at_cap(self):
        self.game.xp = 10 ** 9
        game_mod.check_new_level()
        self.assertEqual(self.game.player_level, max(game_mod.gconfig.levels))

    def test_rank_progression_uses_integer_key(self):
        self.game.qp = 10 ** 9
        game_mod.check_new_rank()
        self.assertEqual(self.game.rank_level, max(game_mod.gconfig.ranks))
        self.assertIsInstance(self.game.rank, str)


class TestItemIntegrity(GameTestCase):
    """Chain: inventory invariants -> no duplicate pickups."""

    def test_key_items_are_unique_and_gems_stay_in_sync(self):
        self.assertTrue(self.game.grant_key_item("Yellow gem"))
        self.assertFalse(self.game.grant_key_item("Yellow gem"))
        self.assertEqual(self.game.key_items.count("Yellow gem"), 1)
        self.assertEqual(self.game.gem_count, 1)
        self.assertTrue(self.game.validate())

    def test_equipment_slots_are_unique(self):
        self.assertTrue(self.game.equip_unique("equipped_weapon", "trident"))
        self.assertFalse(self.game.equip_unique("equipped_weapon", "trident"))
        self.assertEqual(self.game.equipped_weapon, ["trident"])

    def test_trial_completion_grants_gem_once(self):
        self.game.accept_quest("hero's quest")
        self.game.equip_unique("equipped_chest", "desert chestplate")
        self.game.dungeon_kills = 12
        gold_before = self.game.gold
        with mock.patch.object(game_mod, "golden_dunes_scene") as dunes:
            game_mod.desert_trial()
        dunes.assert_called_once()
        self.assertEqual(self.game.key_items, ["Yellow gem"])
        self.assertEqual(self.game.gem_count, 1)
        self.assertEqual(self.game.dungeon_kills, 0)
        self.assertEqual(self.game.gold, gold_before + 10000)
        # the trial node is sealed once its gem is owned
        self.assertFalse(game_mod.can_enter(game_mod.desert_trial))
        with self.assertRaises(game_mod.StoryStateError):
            game_mod.desert_trial()

    def test_shop_cannot_duplicate_chestplate(self):
        self.game.gold = 1000
        self.use_inputs('chestplate', 'chestplate')
        with mock.patch.object(game_mod, "southern_scene"):
            with self.suppress_script_end():
                game_mod.enter_desert_market()
            with self.suppress_script_end():
                game_mod.enter_desert_market()
        self.assertEqual(self.game.equipped_chest.count("desert chestplate"), 1)
        self.assertTrue(self.game.validate())


class TestDeathState(GameTestCase):
    """Chain: death -> no further input, no further battle turns."""

    def test_death_is_terminal_and_blocks_input(self):
        self.use_random(randrange=lambda a, b: 1)  # no miracle revive
        self.game.apply_damage(10 ** 6)
        self.assertFalse(self.game.alive)
        self.assertEqual(self.game.health, 0)
        with self.assertRaises(game_mod.GameOver):
            game_mod.input("next move? ")

    def test_dead_hero_cannot_act_in_scenes(self):
        self.use_random(randrange=lambda a, b: 1)
        self.game.apply_damage(10 ** 6)
        self.use_inputs('east')
        with self.assertRaises(game_mod.GameOver):
            game_mod.crossroads()

    def test_regular_fight_stops_when_hero_dies(self):
        self.game.health = 5
        self.game.str = 1
        # rolls: enemy pick, level 1, 10 dmg per hit, hero does not evade
        self.use_random(randint=queued_randint(0, 1, 10, 50, 100, 1),
                        randrange=lambda a, b: 1)
        self.use_inputs('fight')
        observer = mock.Mock()
        game_mod.attack_regular(observer, 'graveyard')
        self.assertFalse(self.game.alive)
        observer.assert_not_called()          # no post-death scene transition
        self.assertEqual(self.game.gold, 0)   # no reward for a corpse

    def test_bossfight_loop_ends_on_death(self):
        self.game.health = 5
        self.use_random(randint=queued_randint(1, 5, 50, 100, 100, 1),
                        randrange=lambda a, b: 1)
        self.use_inputs('yes')
        observer = mock.Mock()
        game_mod.bossfight(observer)
        self.assertFalse(self.game.alive)
        self.assertNotIn('ancient key', self.game.key_items)
        observer.assert_not_called()

    def test_bossfight_victory_grants_key_once(self):
        self.game.str = 10
        # hero always hits, boss always evaded
        self.use_random(randint=lambda a, b: 1 if a == 1 else a,
                        randrange=lambda a, b: 1)
        self.use_inputs('yes')
        observer = mock.Mock()
        game_mod.bossfight(observer)
        self.assertTrue(self.game.alive)
        self.assertEqual(self.game.key_items.count('ancient key'), 1)
        self.assertEqual(self.game.gold, 1000)
        observer.assert_called_once()
        # a second grant is a no-op, the key stays unique
        self.assertFalse(self.game.grant_key_item('ancient key'))
        self.assertTrue(self.game.validate())


class TestStoryGating(GameTestCase):
    """Chain: every story node requires its legal prerequisites."""

    def test_gated_nodes_are_sealed_on_a_fresh_game(self):
        for node in (game_mod.severed_highlands_scene, game_mod.abyssal_depths_scene,
                     game_mod.desert_trial, game_mod.golden_dunes_scene):
            self.assertFalse(game_mod.can_enter(node), node.__name__)
            with self.assertRaises(game_mod.StoryStateError):
                game_mod.require_node(node)

    def test_open_nodes_are_enterable(self):
        for node in (game_mod.crossroads, game_mod.eastern_scene,
                     game_mod.western_scene, game_mod.southern_scene,
                     game_mod.northern_scene, game_mod.broken_portal):
            self.assertTrue(game_mod.can_enter(node), node.__name__)

    def test_each_prerequisite_unlocks_exactly_its_node(self):
        g = self.game
        # golden dunes needs the chestplate, nothing else
        g.equip_unique("equipped_chest", "desert chestplate")
        self.assertTrue(game_mod.can_enter(game_mod.golden_dunes_scene))
        self.assertFalse(game_mod.can_enter(game_mod.desert_trial))
        # the quest opens the trials
        g.accept_quest("hero's quest")
        self.assertTrue(game_mod.can_enter(game_mod.desert_trial))
        self.assertFalse(game_mod.can_enter(game_mod.broken_portal))
        self.assertFalse(game_mod.can_enter(game_mod.abyssal_depths_scene))
        # the ancient key opens the highlands, and with the quest the depths
        g.grant_key_item('ancient key')
        self.assertTrue(game_mod.can_enter(game_mod.severed_highlands_scene))
        self.assertTrue(game_mod.can_enter(game_mod.abyssal_depths_scene))
        # owning a gem seals its trial again
        g.grant_key_item("Yellow gem")
        self.assertFalse(game_mod.can_enter(game_mod.desert_trial))
        g.grant_key_item("Purple gem")
        self.assertFalse(game_mod.can_enter(game_mod.abyssal_depths_scene))

    def test_direct_scene_calls_enforce_gating(self):
        with self.assertRaises(game_mod.StoryStateError):
            game_mod.golden_dunes_scene()
        with self.assertRaises(game_mod.StoryStateError):
            game_mod.severed_highlands_scene()

    def test_quest_flow_unlocks_trial_through_legal_play(self):
        # crossroads -> east -> south -> accept the quest -> back west
        self.use_inputs('e', 's', 'yes', 'w')
        with self.suppress_script_end():
            game_mod.crossroads()
        self.assertTrue(self.game.has_quest("hero's quest"))
        self.assertTrue(game_mod.can_enter(game_mod.desert_trial))
        self.assertFalse(game_mod.can_enter(game_mod.broken_portal))


class TestSaveLoad(GameTestCase):
    """Chain: save/load must preserve state and reject chapter skips."""

    def setUp(self):
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "save.json")

    def make_midgame_state(self):
        g = self.game
        g.gold = 750
        g.xp = 80
        g.accept_quest("hero's quest")
        g.grant_key_item('ancient key')
        g.equip_unique("equipped_weapon", "trident")
        g.hp_drinks = 3
        g.qp = 4
        g.location = game_mod.eastern_scene
        g.prev_location = game_mod.crossroads
        return g

    def snapshot(self, g):
        return {field: getattr(g, field) for field in game_mod.SAVE_FIELDS}

    def test_roundtrip_preserves_state(self):
        original = self.make_midgame_state()
        game_mod.save_game(self.path)
        restored = game_mod.load_game(self.path)
        for field, value in self.snapshot(original).items():
            self.assertEqual(getattr(restored, field), value, field)
        self.assertIs(restored.location, game_mod.eastern_scene)
        self.assertTrue(restored.validate())

    def test_same_save_consecutive_read_write_is_stable(self):
        self.make_midgame_state()
        game_mod.save_game(self.path)
        with open(self.path) as fh:
            first = fh.read()
        game_mod.load_game(self.path)
        game_mod.save_game(self.path)  # write the just-loaded state again
        with open(self.path) as fh:
            second = fh.read()
        self.assertEqual(first, second)
        again = game_mod.load_game(self.path)
        self.assertEqual(self.snapshot(again), self.snapshot(game_mod.game))

    def test_load_rejects_chapter_skip(self):
        self.make_midgame_state()
        game_mod.save_game(self.path)
        state = json.load(open(self.path))
        # teleport to the highlands without owning the ancient key
        state["location"] = "severed_highlands_scene"
        state["key_items"] = []
        with open(self.path, "w") as fh:
            json.dump(state, fh)
        with self.assertRaises(game_mod.StoryStateError):
            game_mod.load_game(self.path)
        # the recovery path falls back to a fresh, legal game
        recovered = game_mod.load_or_new_game(self.path)
        self.assertTrue(recovered.alive)
        self.assertEqual(recovered.location, "crossroads")

    def test_load_rejects_tampered_attributes(self):
        self.make_midgame_state()
        game_mod.save_game(self.path)
        state = json.load(open(self.path))
        state["dex"] = 999  # out-of-range attribute
        with open(self.path, "w") as fh:
            json.dump(state, fh)
        with self.assertRaises(game_mod.GameError):
            game_mod.load_game(self.path)

    def test_load_rejects_forged_max_health(self):
        self.make_midgame_state()
        game_mod.save_game(self.path)
        state = json.load(open(self.path))
        state["max_health"] += 1  # must derive from attributes
        with open(self.path, "w") as fh:
            json.dump(state, fh)
        with self.assertRaises(game_mod.CorruptSaveError):
            game_mod.load_game(self.path)

    def test_load_rejects_dead_hero(self):
        self.make_midgame_state()
        game_mod.save_game(self.path)
        state = json.load(open(self.path))
        state["alive"] = False
        state["health"] = 0
        with open(self.path, "w") as fh:
            json.dump(state, fh)
        with self.assertRaises(game_mod.CorruptSaveError):
            game_mod.load_game(self.path)

    def test_corrupt_save_recovers_to_new_game(self):
        with open(self.path, "w") as fh:
            fh.write("{ not json at all ")
        recovered = game_mod.load_or_new_game(self.path)
        self.assertTrue(recovered.alive)
        self.assertEqual(recovered.location, "crossroads")
        self.assertTrue(recovered.validate())

    def test_missing_fields_are_corrupt(self):
        with open(self.path, "w") as fh:
            json.dump({"gold": 1000000}, fh)
        with self.assertRaises(game_mod.CorruptSaveError):
            game_mod.load_game(self.path)

    def test_missing_save_file_recovers(self):
        recovered = game_mod.load_or_new_game(self.path)
        self.assertTrue(recovered.alive)

    def test_save_rejects_invalid_live_state(self):
        self.game.gem_count = 3  # gems not backed by key items
        with self.assertRaises(game_mod.GameError):
            game_mod.save_game(self.path)


if __name__ == "__main__":
    unittest.main()
