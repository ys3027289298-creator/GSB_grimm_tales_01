import contextlib
import io
import json
import os
import tempfile
import unittest
from unittest import mock

import code


class GameStateTestCase(unittest.TestCase):
    def setUp(self):
        code.gconfig = code.Config()
        code.gstory = code.Story()
        code.questlist = ['1. slay 10 Bandits\n', '2. slay 10 undead soldiers\n']
        self.game = code.new_game()
        self.game.str = 5
        self.game.res = 5
        self.game.dex = 5
        self.game.recalculate_derived_state()
        self.game.health = self.game.max_health

    def make_legal_sea_state(self):
        self.game.quest = ["hero's quest"]
        self.game.key_items = []
        self.game.add_key_item("Yellow gem")
        self.game.add_key_item("Purple gem")
        self.game.equipped_chest = ["desert chestplate"]
        self.game.location = "sea_scene"
        self.game.prev_location = code.beach_scene
        self.game.dungeon_kills = 3
        return self.game


class AttributeBoundsTests(GameStateTestCase):
    def test_attributes_are_clamped_before_battle_math(self):
        self.game.dex = -20
        self.game.res = -5
        self.game.health = self.game.max_health + 500
        self.game.gold = -10
        self.game.hp_drinks = -2

        self.assertEqual(self.game.dex, 0)
        self.assertEqual(self.game.res, 0)
        self.assertEqual(self.game.health, self.game.max_health)
        self.assertEqual(self.game.gold, 0)
        self.assertEqual(self.game.hp_drinks, 0)

        with mock.patch.object(code.random, "randint", side_effect=[100, 1]):
            self.assertEqual(code.calc_enemy_dmg(7), 7)

        self.game.dex = 999
        self.game.player_dmg = 1
        self.game.str = 1
        self.game.player_level = 1
        with mock.patch.object(code.random, "randint", return_value=100):
            self.assertEqual(code.get_hero_dmg(), 8)

    def test_level_progression_stops_at_configured_boundary(self):
        self.game.xp = 999999
        code.check_new_level()
        self.assertEqual(self.game.player_level, 12)
        self.assertEqual(
            self.game.max_health,
            code.gconfig.default_hero_health + self.game.player_level * 5 + self.game.res * 10,
        )

    def test_trial_enemy_levels_are_not_overwritten_by_fallback_roll(self):
        stage_levels = (
            ("graveyard", 5),
            ("desert trial 1", 15),
            ("desert trial 2", 7),
            ("desert trial 3", 10),
            ("abyssal depths 1", 15),
            ("abyssal depths 2", 7),
            ("abyssal depths 3", 10),
            ("sea scene 1", 15),
            ("sea scene 2", 17),
            ("sea scene 3", 20),
        )
        for location, expected_level in stage_levels:
            with mock.patch.object(code.random, "randint", return_value=expected_level):
                code.randoms(location)
            self.assertEqual(self.game.enemy_level, expected_level, location)


class SaveLoadTests(GameStateTestCase):
    def test_same_save_file_supports_continuous_write_read_cycles(self):
        self.make_legal_sea_state()
        with tempfile.TemporaryDirectory() as directory:
            save_path = os.path.join(directory, "save.json")
            code.save_game(save_path, self.game)
            with open(save_path, "rb") as save_file:
                first_payload = save_file.read()

            first_load = code.load_game(save_path)
            self.assertEqual(code.serialize_game(first_load), code.serialize_game(self.game))

            code.save_game(save_path, first_load)
            with open(save_path, "rb") as save_file:
                second_payload = save_file.read()
            second_load = code.load_game(save_path)

            self.assertEqual(first_payload, second_payload)
            self.assertEqual(code.serialize_game(second_load), code.serialize_game(first_load))
            self.assertIs(code.game, second_load)

    def test_corrupt_save_recovers_without_entering_a_story_node(self):
        sentinel = code.new_game()
        sentinel.location = "crossroads"
        with tempfile.TemporaryDirectory() as directory:
            save_path = os.path.join(directory, "save.json")
            with open(save_path, "w") as save_file:
                save_file.write("{not valid json")

            recovered = code.load_game(save_path, fallback=lambda: sentinel)
            self.assertIs(recovered, sentinel)
            self.assertIs(code.game, sentinel)
            self.assertEqual(recovered.location, "crossroads")

    def test_save_with_illegal_chapter_jump_is_rejected(self):
        self.game.location = "eastern_scene"
        self.game.prev_location = code.crossroads
        sentinel = code.new_game()
        with tempfile.TemporaryDirectory() as directory:
            save_path = os.path.join(directory, "save.json")
            state = code.serialize_game(self.game)
            state["location"] = "sea_scene"
            with open(save_path, "w") as save_file:
                json.dump(state, save_file)

            self.assertIs(code.load_game(save_path, fallback=lambda: sentinel), sentinel)

            state["location"] = "eastern_scene"
            state["prev_location"] = "sea_scene"
            with open(save_path, "w") as save_file:
                json.dump(state, save_file)

            self.assertIs(code.load_game(save_path, fallback=lambda: sentinel), sentinel)

    def test_every_restricted_node_is_revalidated_during_load(self):
        cases = (
            ("broken_portal", {"quest": ["hero's quest"]}),
            ("golden_dunes_scene", {}),
            ("desert_village_scene", {}),
            ("desert_trial", {"equipped_chest": ["desert chestplate"]}),
            ("severed_highlands_scene", {}),
            ("abyssal_depths_scene", {"quest": ["hero's quest"]}),
            ("sea_scene", {"quest": ["hero's quest"]}),
        )
        sentinel = code.new_game()
        with tempfile.TemporaryDirectory() as directory:
            save_path = os.path.join(directory, "save.json")
            self.game.location = "crossroads"
            self.game.prev_location = ""
            code.save_game(save_path, self.game)
            with open(save_path, "r") as save_file:
                base_state = json.load(save_file)

            for location, overrides in cases:
                invalid_state = dict(base_state)
                invalid_state.update(overrides)
                invalid_state["location"] = location
                with open(save_path, "w") as save_file:
                    json.dump(invalid_state, save_file)
                self.assertIs(code.load_game(save_path, fallback=lambda: sentinel), sentinel, location)

    def test_out_of_range_values_are_not_silently_laundered(self):
        sentinel = code.new_game()
        with tempfile.TemporaryDirectory() as directory:
            save_path = os.path.join(directory, "save.json")
            code.save_game(save_path, self.game)
            with open(save_path, "r") as save_file:
                state = json.load(save_file)

            for field, value in (
                ("player_level", 99),
                ("dungeon_kills", 13),
                ("enemy_level", 0),
                ("gold", -1),
                ("health", self.game.max_health + 1),
            ):
                invalid_state = dict(state)
                invalid_state[field] = value
                with open(save_path, "w") as save_file:
                    json.dump(invalid_state, save_file)
                self.assertIs(code.load_game(save_path, fallback=lambda: sentinel), sentinel)

            invalid_state = dict(state)
            invalid_state["quest"] = ["hero's quest"]
            invalid_state["key_items"] = ["Yellow gem", "Yellow gem"]
            invalid_state["gem_count"] = 1
            with open(save_path, "w") as save_file:
                json.dump(invalid_state, save_file)
            self.assertIs(code.load_game(save_path, fallback=lambda: sentinel), sentinel)

    def test_dead_save_round_trips_and_still_blocks_input(self):
        self.game.location = "crossroads"
        self.game.prev_location = ""
        self.game.health = 0
        self.game.dead = True
        self.game.player_status = ["dead"]

        with tempfile.TemporaryDirectory() as directory:
            save_path = os.path.join(directory, "save.json")
            code.save_game(save_path, self.game)
            loaded = code.load_game(save_path)

        self.assertTrue(loaded.dead)
        self.assertEqual(loaded.health, 0)
        with mock.patch("builtins.input") as input_mock:
            with self.assertRaises(code.GameOver):
                code.game_input("anything")
        input_mock.assert_not_called()


class ItemAndStoryGateTests(GameStateTestCase):
    def test_key_items_and_gem_count_are_idempotent(self):
        self.game.add_key_item("Yellow gem")
        self.game.add_key_item("Yellow gem")
        self.game.key_items.append("Yellow gem")
        self.game.quest.append("hero's quest")
        self.game.quest.append("hero's quest")
        self.assertEqual(self.game.key_items, ["Yellow gem"])
        self.assertEqual(self.game.quest, ["hero's quest"])
        self.assertEqual(self.game.gem_count, 1)

    def test_completed_trial_cannot_award_duplicate_gem(self):
        self.game.quest = ["hero's quest"]
        self.game.equipped_chest = ["desert chestplate"]
        self.game.dungeon_kills = 11

        with mock.patch.object(code, "attack_regular", return_value=None) as attack_mock, \
                mock.patch.object(code, "golden_dunes_scene", return_value=None), \
                contextlib.redirect_stdout(io.StringIO()):
            code.desert_trial()
            code.desert_trial()

        self.assertEqual(attack_mock.call_count, 1)
        self.assertEqual(self.game.key_items.count("Yellow gem"), 1)
        self.assertEqual(self.game.gem_count, 1)
        self.assertEqual(self.game.dungeon_kills, 0)

    def test_completed_boss_cannot_award_duplicate_key(self):
        self.game.key_items = ["ancient key"]
        previous_scene = mock.Mock()
        with mock.patch("builtins.input") as input_mock:
            code.bossfight(previous_scene)
        previous_scene.assert_called_once_with()
        input_mock.assert_not_called()
        self.assertEqual(self.game.key_items.count("ancient key"), 1)

    def test_every_restricted_story_node_requires_legal_prerequisites(self):
        self.assertTrue(code.can_enter_scene("broken_portal", self.game))
        self.game.add_quest("hero's quest")
        self.assertFalse(code.can_enter_scene("broken_portal", self.game))

        self.assertFalse(code.can_enter_scene("golden_dunes_scene", self.game))
        self.assertFalse(code.can_enter_scene("desert_village_scene", self.game))
        self.assertFalse(code.can_enter_scene("desert_trial", self.game))
        self.game.equipped_chest = ["desert chestplate"]
        self.assertTrue(code.can_enter_scene("golden_dunes_scene", self.game))
        self.assertTrue(code.can_enter_scene("desert_village_scene", self.game))

        self.assertTrue(code.can_enter_scene("desert_trial", self.game))
        self.game.add_key_item("Yellow gem")
        self.assertFalse(code.can_enter_scene("desert_trial", self.game))

        self.assertFalse(code.can_enter_scene("severed_highlands_scene", self.game))
        self.assertFalse(code.can_enter_scene("abyssal_depths_scene", self.game))
        self.game.add_key_item("ancient key")
        self.assertTrue(code.can_enter_scene("severed_highlands_scene", self.game))

        self.assertTrue(code.can_enter_scene("abyssal_depths_scene", self.game))
        self.assertFalse(code.can_enter_scene("sea_scene", self.game))
        self.game.add_key_item("Purple gem")
        self.assertFalse(code.can_enter_scene("abyssal_depths_scene", self.game))

        self.assertTrue(code.can_enter_scene("sea_scene", self.game))
        self.game.add_key_item("Blue gem")
        self.assertFalse(code.can_enter_scene("sea_scene", self.game))

    def test_begin_scene_blocks_illegal_entry_without_moving_player(self):
        self.game.location = "crossroads"
        self.assertFalse(code.begin_scene("sea_scene"))
        self.assertEqual(self.game.location, "crossroads")


class DeathControlTests(GameStateTestCase):
    def test_death_sets_terminal_state_and_blocks_input(self):
        with mock.patch.object(code.random, "randrange", return_value=1), \
                contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(code.GameOver):
                self.game.die()

        self.assertTrue(self.game.dead)
        self.assertEqual(self.game.health, 0)
        self.assertIn("dead", self.game.player_status)
        with mock.patch("builtins.input") as input_mock:
            with self.assertRaises(code.GameOver):
                code.game_input("continue?")
        input_mock.assert_not_called()

    def test_battle_stops_immediately_after_fatal_damage(self):
        previous_scene = mock.Mock()

        def set_enemy(_location):
            self.game.enemy_level = 1
            self.game.enemy_dmg = 10
            self.game.player_dmg = 0

        self.game.health = 1
        with mock.patch.object(code.random, "randint", return_value=0), \
                mock.patch.object(code.random, "randrange", return_value=1), \
                mock.patch.object(code, "randoms", side_effect=set_enemy), \
                mock.patch.object(code, "calc_enemy_dmg", side_effect=lambda damage: damage), \
                mock.patch.object(code, "get_hero_dmg") as hero_damage_mock, \
                mock.patch("builtins.input", return_value="fight"), \
                contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(code.GameOver):
                code.attack_regular(previous_scene, "graveyard")

        hero_damage_mock.assert_not_called()
        previous_scene.assert_not_called()
        self.assertEqual(self.game.enemy_hp, 50)
        self.assertEqual(self.game.gold, 0)
        self.assertTrue(self.game.dead)


if __name__ == "__main__":
    unittest.main()
