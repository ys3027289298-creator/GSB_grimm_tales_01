
# #imports are always on top
import json
import math
import os
import random
import tempfile


class GameOver(Exception):
    pass


class PlayerRevived(Exception):
    def __init__(self, destination):
        super().__init__("player revived")
        self.destination = destination


def _non_negative_int(value):
    return max(0, int(value))


def _unique_strings(values):
    result = []
    for value in values:
        if not isinstance(value, str):
            raise ValueError("state lists may only contain strings")
        if value and value not in result:
            result.append(value)
    return result


class UniqueStringList(list):
    def append(self, value):
        if not isinstance(value, str):
            raise TypeError("state lists may only contain strings")
        if value and value not in self:
            super().append(value)

    def extend(self, values):
        for value in values:
            self.append(value)

    def insert(self, index, value):
        if not isinstance(value, str):
            raise TypeError("state lists may only contain strings")
        if value and value not in self:
            super().insert(index, value)


def _gem_count(key_items):
    return sum(1 for item in key_items if item.endswith(" gem"))


class Game:
    def __init__(self, gold, xp, health,qp):
        global gconfig
        self._gold = 0
        self._xp = 0
        self._qp = 0
        self._gem_count = 0
        self._str = 0
        self._res = 0
        self._dex = 0
        self._player_level = 1
        self._unspent_points = 0
        self._max_health = 1
        self._health = 0
        self._enemy_level = 1
        self._enemy_hp = 0
        self._player_dmg = 0
        self._enemy_dmg = 0
        self._dungeon_kills = 0
        self._boss_hp = 0
        self._hp_drinks = 0
        self.gold = gold
        self.xp = xp
        self._quest = UniqueStringList()
        self.quest = []
        self.qp = qp
        self.str = random.randrange(1, 7)
        self.res = random.randrange(1, 7)
        self.dex = max(1, gconfig.points - self.str - self.res)
        self.player_level = 1
        self.unspent_points = 0
        self.max_health = health + self.player_level * 5 + self.res * 10
        self.health = self.max_health
        self.enemy_level = 1
        self.enemy_hp = 0
        self.player_dmg = 0
        self.enemy_dmg = 0
        self.dungeon_kills = 0
        self.boss_hp = 500
        self.rank = "stranger"
        self.hp_drinks = 0
        self.equipped_weapon = []
        self.prev_location = ""
        self.location = ""
        self._key_items = UniqueStringList()
        self.key_items = []
        self.equipped_chest = []
        self.equipped_legs = []
        self.equipped_feet = []
        self.equipped_head = []
        self._player_status = UniqueStringList()
        self.player_status = []
        self.dead = False

    @property
    def quest(self):
        return self._quest

    @quest.setter
    def quest(self, value):
        if not isinstance(value, list):
            raise ValueError("quest must be a list")
        self._quest = UniqueStringList(_unique_strings(value))

    @property
    def key_items(self):
        return self._key_items

    @key_items.setter
    def key_items(self, value):
        if not isinstance(value, list):
            raise ValueError("key_items must be a list")
        self._key_items = UniqueStringList(_unique_strings(value))

    @property
    def player_status(self):
        return self._player_status

    @player_status.setter
    def player_status(self, value):
        if not isinstance(value, list):
            raise ValueError("player_status must be a list")
        self._player_status = UniqueStringList(_unique_strings(value))

    @property
    def gold(self):
        return self._gold

    @gold.setter
    def gold(self, value):
        self._gold = _non_negative_int(value)

    @property
    def xp(self):
        return self._xp

    @xp.setter
    def xp(self, value):
        self._xp = _non_negative_int(value)

    @property
    def qp(self):
        return self._qp

    @qp.setter
    def qp(self, value):
        self._qp = _non_negative_int(value)

    @property
    def quest_points(self):
        return self.qp

    @quest_points.setter
    def quest_points(self, value):
        self.qp = value

    @property
    def gem_count(self):
        return self._gem_count

    @gem_count.setter
    def gem_count(self, value):
        self._gem_count = _non_negative_int(value)

    @property
    def str(self):
        return self._str

    @str.setter
    def str(self, value):
        self._str = _non_negative_int(value)

    @property
    def res(self):
        return self._res

    @res.setter
    def res(self, value):
        self._res = _non_negative_int(value)

    @property
    def con(self):
        return self.res

    @con.setter
    def con(self, value):
        self.res = value

    @property
    def dex(self):
        return self._dex

    @dex.setter
    def dex(self, value):
        self._dex = _non_negative_int(value)

    @property
    def player_level(self):
        return self._player_level

    @player_level.setter
    def player_level(self, value):
        self._player_level = min(12, max(1, int(value)))

    @property
    def unspent_points(self):
        return self._unspent_points

    @unspent_points.setter
    def unspent_points(self, value):
        self._unspent_points = _non_negative_int(value)

    @property
    def max_health(self):
        return self._max_health

    @max_health.setter
    def max_health(self, value):
        self._max_health = max(1, int(value))
        if hasattr(self, "_health"):
            self._health = min(self._health, self._max_health)

    @property
    def health(self):
        return self._health

    @health.setter
    def health(self, value):
        self._health = min(max(0, int(value)), self.max_health)

    @property
    def enemy_level(self):
        return self._enemy_level

    @enemy_level.setter
    def enemy_level(self, value):
        self._enemy_level = max(1, int(value))

    @property
    def enemy_hp(self):
        return self._enemy_hp

    @enemy_hp.setter
    def enemy_hp(self, value):
        self._enemy_hp = _non_negative_int(value)

    @property
    def player_dmg(self):
        return self._player_dmg

    @player_dmg.setter
    def player_dmg(self, value):
        self._player_dmg = _non_negative_int(value)

    @property
    def enemy_dmg(self):
        return self._enemy_dmg

    @enemy_dmg.setter
    def enemy_dmg(self, value):
        self._enemy_dmg = _non_negative_int(value)

    @property
    def dungeon_kills(self):
        return self._dungeon_kills

    @dungeon_kills.setter
    def dungeon_kills(self, value):
        self._dungeon_kills = min(12, _non_negative_int(value))

    @property
    def boss_hp(self):
        return self._boss_hp

    @boss_hp.setter
    def boss_hp(self, value):
        self._boss_hp = _non_negative_int(value)

    @property
    def hp_drinks(self):
        return self._hp_drinks

    @hp_drinks.setter
    def hp_drinks(self, value):
        self._hp_drinks = _non_negative_int(value)

    def is_dead(self):
        return self.dead or self.health <= 0

    def has_quest(self, quest_name):
        return quest_name in self.quest

    def add_quest(self, quest_name):
        if quest_name not in self.quest:
            self.quest.append(quest_name)

    def add_key_item(self, item):
        if item not in self.key_items:
            self.key_items.append(item)
        self.gem_count = _gem_count(self.key_items)

    def heal(self, amount):
        self.health = min(self.max_health, self.health + _non_negative_int(amount))

    def spend_gold(self, amount):
        amount = _non_negative_int(amount)
        if self.gold < amount:
            return False
        self.gold -= amount
        return True

    def recalculate_derived_state(self):
        self.max_health = gconfig.default_hero_health + self.player_level * 5 + self.res * 10
        self.health = min(self.health, self.max_health)
        self.gem_count = _gem_count(self.key_items)
        
    def __str__(self):
        return "your level is " + str(self.player_level) + "; you have " + str(self.xp) + " xp" + "\nyou have " + str(self.health) + " hp; you have " + str(self.gold) + " gold" + "\nyour current rank is " + self.rank + "\nyou have " + str(self.gem_count) + " gem/gems"

                
    def die(self):
        self.health = 0
        self.dead = True
        if "dead" not in self.player_status:
            self.player_status.append("dead")
        dice_d20 = random.randrange(1, 20)
        if dice_d20 <= 18:
            print(dice_d20)
            print("you just died")
            raise GameOver("player died")
        else:
            print("looks like you could use some help, let me revive you")
            self.dead = False
            if "dead" in self.player_status:
                self.player_status.remove("dead")
            self.health = self.max_health
            destination = self.prev_location if callable(self.prev_location) else crossroads
            self.prev_location = destination
            raise PlayerRevived(destination)


class Config:
    def __init__(self):
        self.levels = {1: 0, 2: 25, 3: 75, 4: 150, 5: 250, 6: 375, 7: 525, 8: 700, 9: 900, 10: 1150, 11: 1450, 12: 1800}
        self.ranks = {1: 1, 2: 5, 3: 10, 4: 20, 5: 40, 6: 80, 7: 160, 8: 320, 9: 640}
        self.points = 15
        self.hero_chance_to_evade = 0.1
        self.dex_evade_bonus = 0.01
        self.hero_chance_to_hit = 0.7
        self.dex_accuracy_bonus = 0.01
        self.default_hero_health = 100
        self.hp_drink_price = 25
        self.hp_drink_hpower = 50 
        self.damask_sword_price = 1000
        self.damask_sword_atk = 100
        self.trident_price = 500
        self.trident_atk = 50
        self.scarab_blade_price = 5000
        self.scarab_blade_atk = 200
        self.gods_bane_atk = 100000


game = None
gconfig = None
gstory = None
questlist = []


def level_for_xp(xp):
    player_level = 1
    while player_level < 12 and xp >= gconfig.levels[player_level + 1]:
        player_level += 1
    return player_level


def new_game():
    global game
    game = Game(0, 1, gconfig.default_hero_health, 0)
    game.prev_location = ""
    return game


def game_input(prompt):
    if game is not None and game.is_dead():
        raise GameOver("dead players cannot act")
    return input(prompt)


def parse_non_negative_int(value):
    try:
        amount = int(value)
    except (TypeError, ValueError):
        return None
    if amount < 0:
        return None
    return amount


SCENE_REQUIREMENTS = {
    "broken_portal": lambda current_game: not current_game.has_quest("hero's quest"),
    "golden_dunes_scene": lambda current_game: "desert chestplate" in current_game.equipped_chest,
    "desert_village_scene": lambda current_game: "desert chestplate" in current_game.equipped_chest,
    "desert_trial": lambda current_game: "desert chestplate" in current_game.equipped_chest and current_game.has_quest("hero's quest") and "Yellow gem" not in current_game.key_items,
    "severed_highlands_scene": lambda current_game: "ancient key" in current_game.key_items,
    "abyssal_depths_scene": lambda current_game: "ancient key" in current_game.key_items and current_game.has_quest("hero's quest") and "Purple gem" not in current_game.key_items,
    "sea_scene": lambda current_game: "Purple gem" in current_game.key_items and "Blue gem" not in current_game.key_items,
}


def can_enter_scene(scene_id, current_game=None):
    current_game = current_game or game
    requirement = SCENE_REQUIREMENTS.get(scene_id)
    return requirement is None or requirement(current_game)


def begin_scene(scene_id):
    if game is not None and game.is_dead():
        raise GameOver("dead players cannot enter a scene")
    if not can_enter_scene(scene_id):
        return False
    game.location = scene_id
    return True


def return_to_previous_scene():
    destination = game.prev_location if callable(game.prev_location) else crossroads
    destination()

class Story:
    def __init__(self):
        self.beach_story = "You decide to walk barefoot along the clean beach. The waves lap at your feet. you can see someone standing on a dock in the distance"
        self.southern_story = 'A vast expanse of golden sand stretches out just to the south of of you.\n The sandy dunes seem to continue far into the distance. Few have been known to survive the merciless sandstorms that are said to happen in the golden dunes.\n You see a merchent selling survival gear nearby\n'
        self.eastern_story = "'North of you you see a village, to the west of you is a crossroad, to the northwest you see a forest\n South of you you see a portal that appears to be broken,  and to the northeast you see a graveyard\n"
        self.dock_story = '''As you approach the man on the dock the man turns to face you, he then intoduces himself as the captain of a nearby vessal.\n
He claims to be able to be one of the few sailors to be able to cross the torental sea, but to do so it will cost you 100k gold.\n'''

        self.northern_story = '''you unlock the gate with the ancient key.\n 
The sound of a powerful mechanism at work can be heard as the gate slowly opens.\n
In the distance you see a mountain range commonly called The Severed Highlands.\n
Would you like to go to The Severed Highlands, or turn back?\n'''

# -=start code for game endings=-
def ending_cave_collapsed():
    print('As you enter the cave the ceiling collapses behind you')
    print('You decide to leave the cave and emerge through a grove of trees into a forest')
    print('You settle down and live out the rest of your days alone in the peaceful forest\n')
    print('congrats you reached the first ending')


def western_scene():
    ''' commands include north, west and (back/south)'''
    global game
    if not begin_scene("western_scene"):
        return
    print('You moved west')
    decision = game_input('You see a dark cave ahead of you to the north\n And a Sandy Beach to the west of you \nDo you move north, move west, or turn back?\n')
    if decision == 'north' or decision == 'n':
        print('You move into the dark cave\n')
        dice_d20 = random.randrange(1, 20)
        if dice_d20 <= 18:
            attack_regular(western_scene, 'dark cave')
        else:
            ending_cave_collapsed()
    elif decision == 'south' or decision == 'back' or decision == 'turn back':
        print('You move back to the crossroads ')
        game.prev_location = western_scene
        crossroads()
    elif decision == 'west' or decision == 'w':
        print('you run to the sandy beach and dip your feet in the water')
        game.prev_location = western_scene
        beach_scene()
    elif decision == 'help':
        help()

def dock_scene():
    global game
    if not begin_scene("dock_scene"):
        return
    print(gstory.dock_story)
    decision = game_input("would you like to accept his offer, and attempt to cross the sea?\n") ##placeholder
    if decision == "yes" or decision == "y":
        if game.gold >= 100000:
            print('you accept his offer and cross the sea.')
            game.spend_gold(100000)
            print('you win')
            quit()
            ## new continent with many more adventures in stock, possibly start the second game here
        else:
            print("false")
        if game.gold < 100000:
            print("You dont have enough to do this try again at a later date")
            game.prev_location= dock_scene
            beach_scene()
        else:
            print("try again")
            dock_scene()
    elif decision == "no" or decision== "n":
        print(" you decline his offer and return to the beach")
        game.prev_location = dock_scene
        beach_scene()
    elif decision == "gold":
        game.gold += 100000000
        dock_scene()
    elif decision == "help" or decision == "Help":
        help()
    else:
        print(" that is not a choice")
        dock_scene()

    
def beach_scene():
    if not begin_scene("beach_scene"):
        return
    print(gstory.beach_story)
    decision = game_input('would you like to go back to the entrance of the dark cave or check out the sea?\n')
    if decision == 'sea':
        game.prev_location = beach_scene
        #dock_scene()
        decision2=game_input("are you sure this is a dungeon that could easily kill you, would you like to move forward?\n")
        if decision2=="y" or decision2=="yes":
            sea_scene()
    elif decision == 'cave' or decision == 'back':
        game.prev_location = beach_scene
        western_scene()
    elif decision == "help":
        help()
    else:
        print('location not found try again')
        beach_scene()
def dungeon(location):
    global game,gconfig
    if location == 'sea scene ':
        if not begin_scene("sea_scene"):
            return_to_previous_scene()
            return
        run_trial(
            "sea scene",
            sea_scene,
            beach_scene,
            "Blue gem",
            "you have gotten the blue gem as well as the scroll of power!",
            "you read the scroll, written on it is the words 'The next stone was given to the demons by one of the former heros in exchange for near endless power.'\n",
        )


def run_trial(location, entry_scene, return_scene, reward_item, reward_text, scroll_text):
    while True:
        if game.dungeon_kills < 8:
            stage = 1
        elif game.dungeon_kills < 11:
            stage = 2
        elif game.dungeon_kills < 12:
            stage = 3
        else:
            if reward_item not in game.key_items:
                resetDungeons()
                game.add_key_item(reward_item)
                print(reward_text)
                print(scroll_text)
            else:
                game.dungeon_kills = 0
            game.prev_location = return_scene
            return_scene()
            return
        if game.dungeon_kills == 8:
            print('The Second stage of the Trial is starting!')
            heal_at_trial_station()
        elif game.dungeon_kills == 11:
            print('The Third stage of the Trial is starting!')
            heal_at_trial_station()
        game.dungeon_kills += 1
        attack_regular(entry_scene, location + " " + str(stage), True)


def heal_at_trial_station():
    hp_station = math.ceil(game.max_health*0.8)
    if game.health < hp_station:
        restored = hp_station - game.health
        game.health = hp_station
        print(f'The fountain of Health has restored {restored} HP!')
def sea_scene():
    global game,gconfig
    dungeon('sea scene ')
# -=gives the user the choices for the right path=-
def eastern_scene():
    global game
    if not begin_scene("eastern_scene"):
        return
    map(game.location)
    print(gstory.eastern_story)
    decision = game_input('choose either n, w, nw, s or ne\n')
    if decision == 'northeast' or decision == 'ne':
        print('You walk into the graveyard')
        attack_regular(eastern_scene, 'graveyard')
    elif decision == 'nw' and 'ancient key' not in game.key_items:
        bossfight(eastern_scene)
    elif decision == 'n':
        game.prev_location = eastern_scene
        village_scene()
    elif decision == 'w' or decision == 'west':
        game.prev_location = eastern_scene
        crossroads()
    elif (decision == 's' or decision == 'south') and "hero's quest" not in game.quest:
        game.prev_location = eastern_scene
        broken_portal()
    elif decision == 'nw' and 'ancient key' in game.key_items:
        print("you already have defeated this boss")
        eastern_scene()
    elif decision == 'help':
        help()
    else:
        print('sorry, no such option is available\n')
        eastern_scene()


def northern_scene():
    global game,gstory
    if not begin_scene("northern_scene"):
        return
    print('''Two colossal stone statues stand on the sides of a gigantic stone gate.\n
Upon closer inspection of the gate you find a keyhole at the base of one of the doors.\n''')
    if 'ancient key' in game.key_items:
        print(gstory.northern_story)
        decision = game_input('choose either n, or s\n')
        if decision == 'north' or decision == 'n':
            print('You walk to the base of the nearest mountain')
            game.prev_location = northern_scene
            severed_highlands_scene()
        elif decision == 's' or decision == 'south':
            game.prev_location = northern_scene
            crossroads()
        elif decision == 'help':
            help()
    else:
        game.prev_location = northern_scene
        print("finding no way to open the gate you return to the crossroads\n")
        crossroads()
def resetDungeons():
    global game
    print("you cleared the dungeon!")
    print("you got 10,000 gold as a reward")
    game.gold += 10000
    game.dungeon_kills=0
    game.qp+=1
    print("you have ", game.qp,  " questpoints\n")
    print(game)
def severed_highlands_scene():
    global game
    if not begin_scene("severed_highlands_scene"):
        return
    print("you can either go south to the gate or east to the abyssal depths\n")
    decision = game_input('choose either s or e\n')
    if decision == 's' or decision == 'south':
        print("You return to the gate\n")
        game.prev_location = severed_highlands_scene
        northern_scene()
    elif decision == 'e' or decision == 'east':
        if 'Purple gem' not in game.key_items and "hero's quest" in game.quest:
            print(" you see a deep pit and walk towards it\n")
            game.prev_location = severed_highlands_scene
            abyssal_depths_scene()
        elif "hero's quest" not in game.quest:
            print("you have no need to enter. Try to find the quest needed to enter.")
            severed_highlands_scene()
        elif "Purple gem" in game.key_items:
            print("you already have beaten this trial, there is no need to return.\n")
        elif decision == 'help':
            help()
        else:
            print("error")
            severed_highlands_scene()
def abyssal_depths_scene():
    global game,gconfig
    if not begin_scene("abyssal_depths_scene"):
        return
    run_trial(
        "abyssal depths",
        abyssal_depths_scene,
        severed_highlands_scene,
        "Purple gem",
        "you have gotten the Purple gem, you see words inscribed in the wall next to the place where you found the stone",
        " you read the wall it says, ' look under the tides to find where the next stone hides'\n",
    )
def broken_portal():
    global game
    if not begin_scene("broken_portal"):
        return
    print("you see a broken portal ahead of you\n")
    print("The portal has five slots; one slot had a gray gem embedded in the slot. A spirit appears and explains to you the story behind the portal. Once this land had bountiful resources and both the humans and demons lived peaceful lives. But this peace was not to last forever.  One day the Demon armies forces charged through the gate. They destroyed and pillaged everything in sight. Eventually The countries five hero's as well as thier armies stood against the demons in a long war. In the end only one hero remained. He defeated the demon king and returned the demons back to their home world. With the remainder of his strength he destroyed the demon's only way to return to our world, the portal. With the portal out of the way the hero hid the sacred gems throughout the world with the goal of the emons never being allowed to return again. But as of recently the demons have grown more powerful, and have found a way to create a new portal. All of the gems besides the gray one were eventually lost to time. It is now your job to find the remaining gems, repair the portal and defeat the demons that lay within.\n")
    print(" The sprit then reveals that he is the  ghost of that very hero who saved the world\n")
    if game.gem_count==3:
        print(" you enter the gems and the portal opens")
        
    decision = game_input('Would you like to accept this quest?\n')
    if decision == 'y' or decision == 'yes':
        if not game.has_quest("hero's quest"):
            print("You have accepted the hero's quest\n")
            game.add_quest("hero's quest")
            print("you have taken the quest. The spirit tells you the first gem resides where the serpant lies\n")
            game.prev_location = eastern_scene
            eastern_scene()
        else:
            print("You already have this quest\n")
            broken_portal()
    elif decision == 'n' or decision == 'no':
        print("you decline the spirit. He replies 'feel free to reconsider!' you return to the east\n")
        game.prev_location = broken_portal
        eastern_scene()
    else:
        print("that is not an option please try again\n")
        broken_portal()
# -=code for desert path=-
def southern_scene():
    global game
    if not begin_scene("southern_scene"):
        return
    print(gstory.southern_story)
    decision = game_input('choose either north, merchant, or south\n')
    if decision == 'north' or decision == 'n':
        print('You walk back to the crossroad')
        game.prev_location = southern_scene
        crossroads()
    if decision == 'merchant':
        enter_desert_market()
    elif decision == 'south' or decision == 's':
        if 'desert chestplate' in game.equipped_chest:
            print("Knowing you have the necessary gear to enter the desert, you walk to the Golden Dunes.\n ")
            game.prev_location = southern_scene
            golden_dunes_scene()
        elif 'desert chestplate' not in game.equipped_chest:
            print('You do not have the required gear to enter the Golden Dunes try going to the merchant')
            southern_scene()
        elif decision == 'help':
            help()

def golden_dunes_scene():
    global game
    if not begin_scene("golden_dunes_scene"):
        return
    print('''you can move either west to the desert village, north back to the southern pass, or east to the Serpent's Den''')
    decision=game_input('choose either west, north, east\n')
    if decision == 'west' or decision == 'w':
        game.prev_location = golden_dunes_scene
        desert_village_scene()
    elif decision == 'east' or decision == 'e':
        game.prev_location = golden_dunes_scene
        if "hero's quest" in game.quest and "Yellow gem" not in game.key_items:
            desert_trial()
        elif "Yellow gem" in game.key_items:
            print("you already have beaten this trial, there is no need to return.\n")
            golden_dunes_scene()
        else:
            print("you don't have a reason to enter the serpent's den (maybe you are missing a quest?)\n")
            golden_dunes_scene()
    elif decision == 'n' or decision == 'north':
        game.prev_location = golden_dunes_scene
        southern_scene()
    elif decision == 'help':
        print('please, type west, east, or north\n')


def desert_trial():
    global game,gconfig
    if not begin_scene("desert_trial"):
        return
    run_trial(
        "desert trial",
        desert_trial,
        golden_dunes_scene,
        "Yellow gem",
        "you have gotten the Yellow gem as well as the sacred scroll!",
        "you read the sacred scroll, written on it is the words 'The next stone can be found, way down deep under the ground.'\n",
    )
    
    
def desert_village_scene():
    global game
    if not begin_scene("desert_village_scene"):
        return
    print('you entered the desert village')
    village = game_input('''as you enter the village a few establishments stands out to you.
    There are inn, where you could be healed,
    a guild where you could accept quests,
    a shop, where ammunitions could be bought,
    a hero screen, where stat points could be spent, 
    and road to exit of the village. 
    What do you like to visit?\n''')
    if (village == 'inn' or village == 'i') and game.gold >= 100:
        villageinn()
    elif (village == 'inn' or village == 'i') and game.gold < 100:
        print("You can not afford to heal you are {} gold short".format(100 - game.gold))
    elif village == 'shop':
        enter_village_shop()
    elif village == 'guild':
        enter_village_guild()
    elif village == 'hero':
        game.prev_location = desert_village_scene
        enter_hero_screen()
    if village == 'no' or village == 'n' or village == 'exit' or village == 'leave' or village == 'road':
        print("You decide to leave the desert village and return to the golden dunes")
        golden_dunes_scene()


# # code for the desert market
def enter_desert_market():
    global game, gconfig
    if not begin_scene("desert_market"):
        return
    if game.player_level<50:
        shop_choice = game_input('''you see healing drinks, 50g each,
                           and a desert chestplate for 200g. 
                           You have {} gold.
                           What would you like to buy? drinks, or the desert chestplate?
                           Or you wanna leave?\n'''.format(game.gold))
        if (shop_choice == 'drink' or shop_choice == 'drinks'
                or shop_choice == 'healing drink' or shop_choice == 'healing drinks'):
            amount = parse_non_negative_int(game_input('input how many drinks you would like to buy\n'))
            if amount is not None and game.spend_gold(amount * 50):
                game.hp_drinks += amount
                print("You bought your drinks and headed to the exit")
                southern_scene()
            else:
                print("you don't have enough money for that!")
                enter_desert_market()
        elif shop_choice == 'chestplate' or shop_choice == 'desert chestplate' or shop_choice == 'the desert chestplate':
            if game.spend_gold(200):
                game.equipped_chest.append("desert chestplate")
                print("You bought your chestplate, equipped it and headed to the exit")
                southern_scene()
            else:
                print("you don't have enough money for that!")
                enter_desert_market()
    elif game.player_level>=50:
        shop_choice = game_input('''you see healing drinks for 50g each, A Scarab Blade for 5000g,
                           and a desert chestplate for 200g. 
                           You have {} gold.
                           What would you like to buy? drinks, or the desert chestplate?
                           Or you wanna leave?\n'''.format(game.gold))
        if (shop_choice == 'drink' or shop_choice == 'drinks'
                or shop_choice == 'healing drink' or shop_choice == 'healing drinks'):
            amount = parse_non_negative_int(game_input('input how many drinks you would like to buy\n'))
            if amount is not None and game.spend_gold(amount * 50):
                game.hp_drinks += amount
                print("You bought your drinks and headed to the exit")
                southern_scene()
            else:
                print("you don't have enough money for that!")
                enter_desert_market()
        elif shop_choice == 'chestplate' or shop_choice == 'desert chestplate' or shop_choice == 'the desert chestplate':
            if game.spend_gold(200):
                game.equipped_chest.append("desert chestplate")
                print("You bought your chestplate, equipped it and headed to the exit")
                southern_scene()
            else:
                print("you don't have enough money for that!")
                enter_desert_market()
        elif shop_choice == 'blade' or shop_choice == 'scarab blade' or shop_choice == 'a scarab blade':
            if game.spend_gold(gconfig.scarab_blade_price):
                game.equipped_weapon.append("scarab blade")
                print("You bought a Scarab Blade, equipped it and headed to the exit")
                southern_scene()
            else:
                print("you don't have enough money for that!")
                enter_desert_market()


# -=start code for village=-
def village_scene():
    global game
    if not begin_scene("village_scene"):
        return
    print('you entered the village')
    village = game_input('''as you enter the village a few establishments stands out to you.
    There are inn, where you could be healed,
    a guild where you could accept quests,
    a shop, where ammunitions could be bought,
    a hero screen, where stat points could be spent, 
    and road to exit of the village. 
    What do you like to visit?\n''')
    if (village == 'inn' or village == 'i') and game.gold >= 100:
        villageinn()
    elif (village == 'inn' or village == 'i') and game.gold < 100:
        print("You can not afford to heal you are {} gold short".format(100 - game.gold))
    elif village == 'shop':
        enter_village_shop()
    elif village == 'guild':
        enter_village_guild()
    elif village == 'hero':
        game.prev_location = village_scene
        enter_hero_screen()
    if village == 'no' or village == 'n' or village == 'exit' or village == 'leave' or village == 'road':
        print("You decide to leave the village and return to the crossroad")
        eastern_scene()


def enter_hero_screen():
    global game
    if not begin_scene("hero_screen"):
        return
    print(f'''
hp  | {game.health} / {game.max_health}
str | {game.str}
dex | {game.dex}
res | {game.res}
You have {game.unspent_points} to improve stats.
    ''')
    if game.unspent_points>0:
        decision = game_input('Which one you want to improve you have? str, dex, con? or leave to leave\n')
    else:
        decision = game_input('Nothing to do. leave?\n')
    if decision == 'str' and game.unspent_points > 0:
        game.str += 1
        game.unspent_points -= 1
        if game.unspent_points > 0:
            enter_hero_screen()
        return_to_previous_scene()
    elif decision == 'dex' and game.unspent_points > 0:
        game.dex += 1
        game.unspent_points -= 1
        if game.unspent_points > 0:
            enter_hero_screen()
        return_to_previous_scene()
    elif decision == 'con' and game.unspent_points > 0:
        game.con += 1
        game.unspent_points -= 1
        game.recalculate_derived_state()
        if game.unspent_points > 0:
            enter_hero_screen()
        return_to_previous_scene()
    elif decision == "leave":
        return_to_previous_scene()
    else:
        return_to_previous_scene()


def enter_village_guild():
    global game
    if not begin_scene("village_guild"):
        return
    print("the current quests availible are ")
    for x in questlist:
        print(x)
    decision = game_input("you have one availible quest slot which quest would you like to take 1 or 2?\n")
    if decision == '1':
        print("you chose quest 1")
        game.quest = [questlist[0]]
        village_scene()
    elif decision == '2':
        print("you chose quest 2")
        game.quest = [questlist[1]]
        village_scene()


##code for the shop
def enter_village_shop():
    global game, gconfig
    if not begin_scene("village_shop"):
        return
    shop_choice = game_input(f'''    You see healing drinks, {gconfig.hp_drink_price}g each,
a trident for {gconfig.trident_price} and 
the damassk steel sword for {gconfig.damask_sword_price}. 
You have {game.gold} gold.
What would you like to buy? drinks, trident or the sword?
Or you wanna leave?''')
    if (shop_choice == 'drink' or shop_choice == 'drinks'
            or shop_choice == 'healing drink' or shop_choice == 'healing drinks'):
        amount = parse_non_negative_int(game_input('input how many drinks you would like to buy\n'))
        if amount is not None and game.spend_gold(amount * gconfig.hp_drink_price):
            game.hp_drinks += amount
            print("You bought your drinks and headed to the exit")
            village_scene()
        else:
            print("you don't have enough money for that!")
            enter_village_shop()
    elif shop_choice == 'sword' or shop_choice == 'the sword' or shop_choice == 'the damassk steel sword':
        if game.spend_gold(gconfig.damask_sword_price):
            game.equipped_weapon.append("damassk sword")
            print("You bought your sword, swing it over your shoulder and headed to the exit")
            village_scene()
        else:
            print("you don't have enough money for that!")
            enter_village_shop()
    elif shop_choice == 'trident':
        if game.spend_gold(gconfig.trident_price):
            game.equipped_weapon.append("trident")
            print("You bought your trident, swung it over your shoulder and headed to the exit")
            village_scene()
        else:
            print("you dont have enough money for that!")
            enter_village_shop()
    else:
        village_scene()


##code for the village
def villageinn():
    global game
    if not begin_scene("village_inn"):
        return
    print('you enter the inn\n')
    choiceinn = game_input('for 100 gold you can rest to full hp. Would you like to do so?\n')
    if choiceinn == 'yes' or choiceinn == 'y':
        if game.spend_gold(100):
            print(game.max_health)
            healamount  = game.max_health - game.health
            game.health = game.max_health
            print("you have restored {} hp in the inn".format(healamount))
            print("Now healed you leave the village and return to the crossroads")
            village_scene()
        else:
            print("You can not afford to heal you are {} gold short".format(100 - game.gold))
    elif choiceinn == 'no' or choiceinn == 'n':
        print('you have have gone too far there is no turning back')
##end code for village ============================================================================================================


def calc_enemy_dmg(enemy_base_dmg):
    global game
    chance_to_evade = min(100, max(0, (round(gconfig.hero_chance_to_evade + game.dex * gconfig.dex_evade_bonus, 2))*100))
    chance_to_evade = chance_to_evade
    roll_5d20 = random.randint(1, 100)
    status_inflict = random.randint(1,50 + game.res)
    if roll_5d20 <= chance_to_evade:
        print("Your chance to evade is ", chance_to_evade, "%")
        print("You rolled ", roll_5d20, ", and thus enemy missed")
        enemy_base_dmg = 0
    return enemy_base_dmg


def get_hero_dmg():
    global game, gconfig
    calc_player_dmg = game.player_dmg + (2 ** game.player_level) + game.str * 5
    # please note, you should take in DECREMENTAL ORDER BY ATK POWER
    if 'gods_bane' in game.equipped_weapon:
        calc_player_dmg += gconfig.gods_bane_atk
    elif 'scarab blade' in game.equipped_weapon:
        calc_player_dmg += gconfig.scarab_blade_atk
        #print('your attack is improved by your scarab blade')
    elif 'damassk sword' in game.equipped_weapon:
        calc_player_dmg += gconfig.damask_sword_atk
        #print('your attack is improved by your damassk sword')
    elif 'trident' in game.equipped_weapon:
        calc_player_dmg += gconfig.trident_atk
        #print('your attack is improved by your trident')
    chance_to_hit = min(100, max(0, round(gconfig.hero_chance_to_hit + game.dex * gconfig.dex_accuracy_bonus, 2)*100))
    roll_5d20 = random.randint(1, 100)
    if roll_5d20 > chance_to_hit:
        print("Your chance to hit is", chance_to_hit, "%")
        print("You rolled ", roll_5d20, ", and thus you have missed")
        calc_player_dmg = 0
    return calc_player_dmg


def check_new_level():
    global game, gconfig
    bool_level_changed = False
    while game.player_level < 12 and game.xp >= gconfig.levels[game.player_level+1]:
        bool_level_changed = True
        game.player_level += 1
        game.unspent_points += 1
        stat_increase = random.randint(1, 3)
        if stat_increase == 1:
            game.str += 1
        elif stat_increase == 2:
            game.dex += 1
        elif stat_increase == 3:
            game.res += 1
    if bool_level_changed:
        game.recalculate_derived_state()
def check_new_rank():
    global game, gconfig
    return

# -=code for battles=-
def attack_regular(previous_scene, location=None, trial=False):
    global game, gconfig
    if not trial:
        print(location)
    if location == "desert trial 1":
        enemy_list = ['scorpion', 'snake']
        enemy_name = enemy_list[random.randint(0, len(enemy_list)-1)]
    elif location == "desert trial 2":
        enemy_list = ['champ of scroptions', 'champ of snakes']
        enemy_name = enemy_list[random.randint(0, len(enemy_list)-1)]
    elif location == "desert trial 3":
        enemy_list = ['manticore', 'sphinx']
        enemy_name = enemy_list[random.randint(0, len(enemy_list)-1)]
    elif location == "abyssal depths 1":
        enemy_list = ['lesser demon', 'ghoul']
        enemy_name = enemy_list[random.randint(0, len(enemy_list)-1)]
    elif location == "abyssal depths 2":
        enemy_list = ['shade', 'cursed golem']
        enemy_name = enemy_list[random.randint(0, len(enemy_list)-1)]
    elif location == "abyssal depths 3":
        enemy_list = ['soul eater', 'greater demon']
        enemy_name = enemy_list[random.randint(0, len(enemy_list)-1)]
    elif location == "sea scene 1":
        enemy_list = ['great white', 'pirate']
        enemy_name = enemy_list[random.randint(0, len(enemy_list)-1)]
    elif location == "sea scene 2":
        enemy_list = ['mermaid', 'giant squid']
        enemy_name = enemy_list[random.randint(0, len(enemy_list)-1)]
    elif location == "sea scene 3":
        enemy_list = ['kracken', 'ghoul pirates']
        enemy_name = enemy_list[random.randint(0, len(enemy_list)-1)]
    elif location == "graveyard":
        enemy_list = ['zombie', 'undead soldier', 'undead archer']
        enemy_name = enemy_list[random.randint(0, len(enemy_list)-1)]
    elif location == "dark cave":
        enemy_list = ['bat', 'spider', 'undead archer']
        enemy_name = enemy_list[random.randint(0, len(enemy_list) - 1)]
    else:
        enemy_list = ['bat', 'zombie', 'wolf', 'undead']
        enemy_name = enemy_list[random.randint(0, len(enemy_list) - 1)]
    randoms(location)
    game.enemy_hp = game.enemy_level * 50
    print('A level', game.enemy_level, enemy_name, ' appears it has', game.enemy_hp, 'hp')
    trial_locations = ['desert trial 1', 'desert trial 2', 'desert trial 3', 'abyssal depths 1','abyssal depths 2','abyssal depths 3','sea scene 1', 'sea scene 2', 'sea scene 3']
    if location in trial_locations:
        decision = 'fight'
    else:
        decision = game_input('fight or flee?\n')
    if decision == 'fight' or decision =='1':
        while game.enemy_hp > 0:
            enemy_dmg = calc_enemy_dmg(game.enemy_dmg)
            if enemy_dmg != 0:
                game.health = game.health - enemy_dmg
                print('The enemy did', enemy_dmg, 'damage,', 'you have', game.health, 'health')
            if game.health <= 0:
                game.die()
            else:
                if game.health < 25 and game.hp_drinks > 0:
                    game.hp_drinks -= 1
                    game.heal(50)
                    print("you drink a hp drink vital and restored 50 health by this")
                player_dmg = get_hero_dmg()
                game.enemy_hp = game.enemy_hp - player_dmg
                if player_dmg != 0:
                    if game.enemy_hp <= 0:
                        game.enemy_hp=0
                    print('You did', player_dmg, 'damage,', 'the enemy has', game.enemy_hp, 'hp\n')
        if game.enemy_hp <= 0:
            game.gold += 50
            game.xp += game.enemy_level * 3
            check_new_level()
            ##check_new_rank()
            if not trial:
                print(game)
            if trial:
                return
            previous_scene()
    elif decision == 'flee':
        previous_scene()
    else:
        print('no such way!')
        attack_regular(previous_scene, location)


def bossfight(previous_scene):
    global game, gconfig
    if 'ancient key' in game.key_items:
        previous_scene()
        return
    randoms()
    decision = game_input("Are you sure you want to progress, there is a strong enemy ahead?\n")
    if decision == 'turn back' or decision == 'back' or decision == 'no':
        previous_scene()
    else:
        print("A Goblin King appears, he towers over you")
        print('And he has', game.boss_hp, 'hp')
        while game.boss_hp > 0:
            bossdam = random.randint(20, 100)
            bossdam = calc_enemy_dmg(bossdam)
            game.health = game.health - bossdam
            print('The enemy did', bossdam, 'damage,', 'you have', game.health, 'health')
            if game.health <= 0:
                game.die()
            if game.health < 25 and game.hp_drinks > 0:
                game.hp_drinks -= 1
                game.heal(50)
                print("you drink a hp drink vital and restored 50 health by this")
            player_dmg = get_hero_dmg()
            game.boss_hp = game.boss_hp - player_dmg
            if player_dmg == 0:
                print('You missed!\n')
            else:
                if game.boss_hp <= 0:
                    game.boss_hp = 0
                print('You did', player_dmg, 'damage,', 'the enemy has', game.boss_hp, 'hp\n')
        if game.boss_hp <= 0 and game.health > 0:
            game.gold += 1000
            game.xp   += 500
            check_new_level()
            print(game)
            game.add_key_item('ancient key')
            print("you have obtained the ancient key, maybe it opens something?")
            previous_scene()


# -=code for the inital choice=-
def map(scene):
    global game
    map = ''
    if game.location == "crossroads":
        map = '''The World's Map on The Crossroads Sign:

                      North    
                        ||           
        West========Crossroads========East
                        ||                    
                      South            
                               
          '''
    if game.location == "eastern_scene":
        map = '''The World's Map on The Crossroads Sign:

                     Forest   Village Graveyard
                          \\    ||    //
        Crossroads=============East
                                || 
                           Broken Portal 
                     
                               
          '''
    print(map)

def crossroads():
    global game, test2
    if not begin_scene("crossroads"):
        return
    # TBC - to be created by gods of the World
    map(game.location)
    decision = game_input(
        '''You find yourself at The Crossroad, which seems the center of the world.
Do you want to move west, south, north, or move east? (type commands like w or west) \n''')

    if decision == 'east' or decision == 'e':
        game.prev_location = crossroads
        eastern_scene()
        return
    elif decision == 'west' or decision == 'w':
        game.prev_location = crossroads
        western_scene()
    elif decision == 'north' or decision == 'n':
        game.prev_location = crossroads
        northern_scene()
    elif decision == 'south' or decision == 's':
        game.prev_location = crossroads
        southern_scene()
    elif decision == 'help':
        help()
        crossroads()
    elif decision == 'debug':
        gconfig.hero_chance_to_evade = 0.1
        game.hp_drinks = 20
        game.dex = 999
        game.res = 999
        game.str = 999
        game.equipped_weapon = ['gods_bane']
        game.equipped_chest = ['desert chestplate']
        game.equipped_head = ['developers_crown']
        game.gold = 10000
        game.key_items=['ancient key']
        crossroads()
    else:
        print('sorry, no such option is available\n')
        crossroads()
    # #end code for the crossroads scene


def randoms(enemy_location=None):
    global game
    # -=code for randomized variable=-
    if enemy_location == 'desert trial 2':
        game.enemy_level = random.randint(5, 7)
    elif enemy_location == 'desert trial 3':
        game.enemy_level = random.randint(7, 10)
    elif enemy_location == 'abyssal depths 2':
        game.enemy_level = random.randint(5, 7)
    elif enemy_location == 'abyssal depths 3':
        game.enemy_level = random.randint(7, 10)
    elif enemy_location == 'sea scene 2':
        game.enemy_level = random.randint(15, 17)
    elif enemy_location == 'sea scene 3':
        game.enemy_level = random.randint(17, 20)
    elif enemy_location in ['desert trial 1', 'abyssal depths 1', 'sea scene 1']:
        game.enemy_level = random.randint(11, 15)
    else:
        game.enemy_level = random.randint(1, 5)
    game.enemy_dmg = random.randint(5, 10)
    game.player_dmg = random.randint(50, 100)
def help():
    global game
    loc = game.location
    commands = ""
    print("Basic commands include: north, south, east, west\n")
    answer = game_input("to continue to more advaced help type more, to return to the game type exit\n")
    if answer == "more":
        if game.location == "northern_scene":
            commands = "choose a direction, your options include: north or south"
        elif game.location == "southern_scene":
            commands =  " your options include: north, merchant, or south"
        elif game.location == "eastern_scene":
            commands = "choose a direction, your options include: north, west, north-west, south or north-east"
        elif game.location == "western_scene":
            commands = "choose a direction, your options include: north, west and (back/south)"
        elif game.location == "crossroads":
            commands = " choose a direction, your options include: north south east or west"
        print(commands)
        help()
    elif answer == "exit":
        if game.location == "northern_scene":
            northern_scene()
        elif game.location == "southern_scene":
            southern_scene()
        elif game.location == "eastern_scene":
            eastern_scene()
        elif game.location == "western_scene":
            western_scene()
        elif game.location == "crossroads":
            crossroads()
    elif answer != "more" and answer !="exit":
        print(game.location)
        help()


SCENE_FUNCTIONS = {
    "crossroads": crossroads,
    "western_scene": western_scene,
    "beach_scene": beach_scene,
    "dock_scene": dock_scene,
    "sea_scene": sea_scene,
    "eastern_scene": eastern_scene,
    "northern_scene": northern_scene,
    "severed_highlands_scene": severed_highlands_scene,
    "abyssal_depths_scene": abyssal_depths_scene,
    "broken_portal": broken_portal,
    "southern_scene": southern_scene,
    "golden_dunes_scene": golden_dunes_scene,
    "desert_trial": desert_trial,
    "desert_village_scene": desert_village_scene,
    "desert_market": enter_desert_market,
    "village_scene": village_scene,
    "hero_screen": enter_hero_screen,
    "village_guild": enter_village_guild,
    "village_shop": enter_village_shop,
    "village_inn": villageinn,
}


SAVE_VERSION = 1
SAVE_FIELDS = (
    "gold",
    "xp",
    "qp",
    "gem_count",
    "str",
    "res",
    "dex",
    "player_level",
    "unspent_points",
    "max_health",
    "health",
    "enemy_level",
    "enemy_hp",
    "player_dmg",
    "enemy_dmg",
    "dungeon_kills",
    "boss_hp",
    "rank",
    "hp_drinks",
    "dead",
)
SAVE_LIST_FIELDS = (
    "quest",
    "equipped_weapon",
    "key_items",
    "equipped_chest",
    "equipped_legs",
    "equipped_feet",
    "equipped_head",
    "player_status",
)


def scene_ref_to_id(scene_ref):
    if scene_ref == "":
        return ""
    if isinstance(scene_ref, str):
        if scene_ref in SCENE_FUNCTIONS:
            return scene_ref
        raise ValueError("unknown story node")
    for scene_id, scene_function in SCENE_FUNCTIONS.items():
        if scene_ref == scene_function:
            return scene_id
    raise ValueError("unknown story node")


def scene_id_to_ref(scene_id):
    if scene_id == "":
        return ""
    try:
        return SCENE_FUNCTIONS[scene_id]
    except KeyError:
        raise ValueError("unknown story node")


def serialize_game(current_game=None):
    current_game = current_game or game
    state = {
        "version": SAVE_VERSION,
        "location": scene_ref_to_id(current_game.location),
        "prev_location": scene_ref_to_id(current_game.prev_location),
    }
    for field in SAVE_FIELDS:
        state[field] = getattr(current_game, field)
    for field in SAVE_LIST_FIELDS:
        state[field] = list(getattr(current_game, field))
    return state


def save_game(path, current_game=None):
    current_game = current_game or game
    payload = json.dumps(serialize_game(current_game), indent=2, sort_keys=True)
    directory = os.path.dirname(os.path.abspath(path))
    fd, temporary_path = tempfile.mkstemp(prefix=".grimm-save-", dir=directory, text=True)
    try:
        with os.fdopen(fd, "w") as save_file:
            save_file.write(payload)
        os.replace(temporary_path, path)
    except Exception:
        try:
            os.unlink(temporary_path)
        except OSError:
            pass
        raise


def _require_int(data, field):
    value = data[field]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(field + " must be an integer")
    return value


def _require_non_negative_int(data, field):
    value = _require_int(data, field)
    if value < 0:
        raise ValueError(field + " must be non-negative")
    return value


def _restore_game_from_state(data):
    global gconfig, gstory, questlist
    if gconfig is None:
        gconfig = Config()
    if gstory is None:
        gstory = Story()
    if not questlist:
        questlist = ['1. slay 10 Bandits\n', '2. slay 10 undead soldiers\n']
    if not isinstance(data, dict) or data.get("version") != SAVE_VERSION:
        raise ValueError("unsupported save data")

    required_fields = ("location", "prev_location") + SAVE_FIELDS + SAVE_LIST_FIELDS
    for field in required_fields:
        if field not in data:
            raise ValueError("missing save field: " + field)

    restored = Game(0, 0, gconfig.default_hero_health, 1)
    restored.str = _require_non_negative_int(data, "str")
    restored.res = _require_non_negative_int(data, "res")
    restored.dex = _require_non_negative_int(data, "dex")
    player_level = _require_non_negative_int(data, "player_level")
    if player_level not in range(1, 13):
        raise ValueError("player level out of range")
    restored.player_level = player_level
    max_health = _require_non_negative_int(data, "max_health")
    if max_health < 1:
        raise ValueError("max health out of range")
    restored.max_health = max_health
    expected_max_health = gconfig.default_hero_health + restored.player_level * 5 + restored.res * 10
    if restored.max_health != expected_max_health:
        raise ValueError("max health does not match character state")

    restored.gold = _require_non_negative_int(data, "gold")
    restored.xp = _require_non_negative_int(data, "xp")
    restored.qp = _require_non_negative_int(data, "qp")
    restored.gem_count = _require_non_negative_int(data, "gem_count")
    restored.unspent_points = _require_non_negative_int(data, "unspent_points")
    enemy_level = _require_non_negative_int(data, "enemy_level")
    if enemy_level < 1:
        raise ValueError("enemy level out of range")
    restored.enemy_level = enemy_level
    restored.enemy_hp = _require_non_negative_int(data, "enemy_hp")
    restored.player_dmg = _require_non_negative_int(data, "player_dmg")
    restored.enemy_dmg = _require_non_negative_int(data, "enemy_dmg")
    dungeon_kills = _require_non_negative_int(data, "dungeon_kills")
    if dungeon_kills > 12:
        raise ValueError("dungeon kills out of range")
    restored.dungeon_kills = dungeon_kills
    restored.boss_hp = _require_non_negative_int(data, "boss_hp")
    restored.hp_drinks = _require_non_negative_int(data, "hp_drinks")

    for field in SAVE_LIST_FIELDS:
        value = data[field]
        if not isinstance(value, list):
            raise ValueError(field + " must be a list")
        if len(value) != len(set(value)):
            raise ValueError(field + " contains duplicate items")
        setattr(restored, field, _unique_strings(value))

    allowed_key_items = {
        "ancient key",
        "Yellow gem",
        "Purple gem",
        "Blue gem",
    }
    allowed_weapons = {
        "gods_bane",
        "scarab blade",
        "damassk sword",
        "trident",
    }
    allowed_equipment = {
        "desert chestplate",
        "developers_crown",
    }
    if any(item not in allowed_key_items for item in restored.key_items):
        raise ValueError("unknown key item")
    if any(item not in allowed_weapons for item in restored.equipped_weapon):
        raise ValueError("unknown weapon")
    for field in ("equipped_chest", "equipped_legs", "equipped_feet", "equipped_head"):
        if any(item not in allowed_equipment for item in getattr(restored, field)):
            raise ValueError("unknown equipment")

    if not isinstance(data["rank"], str) or not data["rank"]:
        raise ValueError("rank must be a nonempty string")
    restored.rank = data["rank"]
    if not isinstance(data["dead"], bool):
        raise ValueError("dead must be a boolean")
    restored.dead = data["dead"]

    health = _require_non_negative_int(data, "health")
    if health > restored.max_health:
        raise ValueError("health out of range")
    restored.health = health
    if restored.dead != (restored.health == 0):
        raise ValueError("dead state does not match health")
    if restored.dead:
        if "dead" not in restored.player_status:
            restored.player_status.append("dead")
    elif "dead" in restored.player_status:
        restored.player_status.remove("dead")

    if restored.player_level != level_for_xp(restored.xp):
        raise ValueError("player level does not match xp")

    if "ancient key" not in restored.key_items and restored.boss_hp <= 0:
        raise ValueError("unresolved boss state")
    gem_order = ("Yellow gem", "Purple gem", "Blue gem")
    found_gems = [gem for gem in gem_order if gem in restored.key_items]
    if found_gems and not restored.has_quest("hero's quest"):
        raise ValueError("gems require hero's quest")
    for earlier_gem, later_gem in zip(gem_order, gem_order[1:]):
        if later_gem in restored.key_items and earlier_gem not in restored.key_items:
            raise ValueError("gem story order is invalid")
    restored.gem_count = _gem_count(restored.key_items)
    if restored.gem_count != data["gem_count"]:
        raise ValueError("gem count does not match key items")

    restored.location = scene_ref_to_id(data["location"])
    restored.prev_location = scene_id_to_ref(scene_ref_to_id(data["prev_location"]))
    if restored.location and not can_enter_scene(restored.location, restored):
        raise ValueError("story node requirements are not satisfied")
    if restored.prev_location and not can_enter_scene(scene_ref_to_id(restored.prev_location), restored):
        raise ValueError("previous story node requirements are not satisfied")
    return restored


def load_game(path, fallback=None):
    global game
    try:
        with open(path, "r") as save_file:
            data = json.load(save_file)
        restored = _restore_game_from_state(data)
    except (OSError, ValueError, TypeError, KeyError):
        if fallback is None:
            restored = new_game()
        elif callable(fallback):
            restored = fallback()
        else:
            restored = fallback
    game = restored
    return restored


gconfig = Config()
gstory = Story()
questlist = ['1. slay 10 Bandits\n', '2. slay 10 undead soldiers\n']
game = None


def run_game():
    new_game()
    print(" Hello there! Welcome to the world of Grimm!")
    print("\nMy name is Arcus but you can call me The Narrator of this story, as well as the God of this world!")
    print("\nThis world is a vast place, called Grimm inhabited by many creatures\n")
    current_scene = crossroads
    while True:
        try:
            current_scene()
            return
        except PlayerRevived as revived:
            current_scene = revived.destination
        except GameOver:
            return


if __name__ == "__main__":
    run_game()
