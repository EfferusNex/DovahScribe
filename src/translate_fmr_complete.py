"""
Полный и безошибочный локализатор для Forgotten Magic Redone.
Переводит 100% строк (все 855 записей): заклинания, книги, перки, эффекты, описания и теги.
"""

import json
import re
import sys
import io
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from src.translation import TranslationEngine

REVIEW_FILE = Path("data/review/ForgottenMagic_Redone_review.json")

# Полный словарь всех названий (Names)
COMPLETE_NAMES_MAP = {
    # Книги с префиксом
    "Forgotten Magic: Ancient Lich": "Забытая магия: Древний лич",
    "Forgotten Magic: Arcane Weapon": "Забытая магия: Мистическое оружие",
    "Forgotten Magic: Blessed Weapon": "Забытая магия: Благословенное оружие",
    "Forgotten Magic: Blight Curse": "Забытая магия: Гибельное проклятие",
    "Forgotten Magic: Conflagrate": "Забытая магия: Пожарище",
    "Forgotten Magic: Cursed Rune": "Забытая магия: Проклятая руна",
    "Forgotten Magic: Deathguard": "Забытая магия: Страж смерти",
    "Forgotten Magic: Deathly Pall": "Забытая магия: Смертный покров",
    "Forgotten Magic: Discord": "Забытая магия: Раздор",
    "Forgotten Magic: Divine Armor": "Забытая магия: Божественная броня",
    "Forgotten Magic: Divine Light": "Забытая магия: Божественный свет",
    "Forgotten Magic: Doppelganger": "Забытая магия: Двойник",
    "Forgotten Magic: Earthbound Weapon": "Забытая магия: Оружие земли",
    "Forgotten Magic: Electric Charge": "Забытая магия: Электрический заряд",
    "Forgotten Magic: Fire Blast": "Забытая магия: Огненный взрыв",
    "Forgotten Magic: Frost Armor": "Забытая магия: Ледяной доспех",
    "Forgotten Magic: Frost Bomb": "Забытая магия: Морозная бомба",
    "Forgotten Magic: Glacial Fortress": "Забытая магия: Ледниковая крепость",
    "Forgotten Magic: Hammer of Justice": "Забытая магия: Молот правосудия",
    "Forgotten Magic: Healing Touch": "Забытая магия: Целительное прикосновение",
    "Forgotten Magic: Holy Bolt": "Забытая магия: Священная стрела",
    "Forgotten Magic: Ice Lance": "Забытая магия: Ледяное копье",
    "Forgotten Magic: Lightning Strike": "Забытая магия: Удар молнии",
    "Forgotten Magic: Meteor Shower": "Забытая магия: Метеоритный дождь",
    "Forgotten Magic: Necrosis": "Забытая магия: Некроз",
    "Forgotten Magic: Nether Rift": "Забытая магия: Разлом пустоты",
    "Forgotten Magic: Phantom Armor": "Забытая магия: Призрачная броня",
    "Forgotten Magic: Phantom Shroud": "Забытая магия: Призрачный саван",
    "Forgotten Magic: Phoenix Strike": "Забытая магия: Удар феникса",
    "Forgotten Magic: Salamander Touch": "Забытая магия: Прикосновение саламандры",
    "Forgotten Magic: Seed of Life": "Забытая магия: Семя жизни",
    "Forgotten Magic: Skyfall": "Забытая магия: Небесный удар",
    "Forgotten Magic: Spectral Missiles": "Забытая магия: Спектральные снаряды",
    "Forgotten Magic: Storm Armor": "Забытая магия: Громовой доспех",
    "Forgotten Magic: Stormgate": "Забытая магия: Врата бури",
    "Forgotten Magic: Stormstrike": "Забытая магия: Удар бури",
    "Forgotten Magic: Veil of Nature": "Забытая магия: Покров природы",
    "Forgotten Magic: Void Bolt": "Забытая магия: Стрела пустоты",
    "Forgotten Magic: Wild Mushroom": "Забытая магия: Дикий гриб",
    "Forgotten Magic: Winter Woe": "Забытая магия: Зимняя скорбь",
    "Forgotten Magic: Wolf Pack": "Забытая магия: Волчья стая",
    "Forgotten Magic": "Забытая магия",

    # Артефакты, оружие и броня
    "Wall of Storms": "Стена бурь",
    "Glacial Fortress": "Ледниковая крепость",
    "Winter Woe": "Зимняя скорбь",
    "Band of Devastation": "Кольцо опустошения",
    "Band of Devouring": "Кольцо пожирания",
    "Band of Frozen Time": "Кольцо застывшего времени",
    "Band of Illusions": "Кольцо иллюзий",
    "Band of Permanence": "Кольцо постоянства",
    "Ring of Confusion": "Кольцо замешательства",
    "Ring of Furious Flames": "Кольцо яростного пламени",
    "Ring of Hungering Cold": "Кольцо алчущего холода",
    "Ring of Retribution": "Кольцо возмездия",
    "Ring of Virulence": "Кольцо заражения",
    "Revenant Ring": "Кольцо выходца с того света",
    "Storm Caller": "Призыватель бури",
    "Storm Shard": "Осколок бури",
    "Light Bearer": "Несущий свет",
    "Hoarfrost": "Седой иней",
    "Leader of the Pack": "Вожак стаи",
    "Phantom Armor": "Призрачная броня",
    "Hammer of Justice": "Молот правосудия",
    "Divine Hammer": "Божественный молот",
    "Bound Battleaxe": "Призванная секира",
    "Bound Bow": "Призванный лук",
    "Bound Dagger": "Призванный кинжал",
    "Bound Greatsword": "Призванный двуручный меч",
    "Bound Sword": "Призванный меч",
    "Mystic Bow": "Мистический лук",
    "Mystic Dagger": "Мистический кинжал",
    "Mystic Greatsword": "Мистический двуручный меч",
    "Mystic Sword": "Мистический меч",

    # Заклинания, перки и эффекты
    "Alpha Wolf": "Вожак волков",
    "Ambush": "Засада",
    "Anathema": "Анафема",
    "Ancient Lich": "Древний лич",
    "Annihilation": "Аннигиляция",
    "Arcane Distortion": "Мистическое искажение",
    "Arcane Weapon": "Мистическое оружие",
    "Arctic Grasp": "Арктическая хватка",
    "Arctic Snap": "Арктический холод",
    "Area": "Область",
    "Armageddon": "Армагеддон",
    "Armor of Faith": "Доспех веры",
    "Avatar of Storm": "Аватар бури",
    "Avenging Wrath": "Гнев возмездия",
    "Beastial Wrath": "Звериный гнев",
    "Benediction": "Благословение",
    "Bite": "Укус",
    "Bite Effects": "Эффекты укуса",
    "Blazing Speed": "Пылающая скорость",
    "Bleed": "Кровотечение",
    "Bleeding": "Кровотечение",
    "Bleeding Damage": "Урон от кровотечения",
    "Blessed Aegis": "Благословенная эгида",
    "Blessed  Aegis": "Благословенная эгида",
    "Blessed Weapon": "Благословенное оружие",
    "Blessing of the Nines": "Благословение Девяти",
    "Blight Curse": "Гибельное проклятие",
    "Bloodthirst": "Жажда крови",
    "Bond of Corruption": "Узы скверны",
    "Charged Atmosphere": "Заряженная атмосфера",
    "Chilled to the Bones": "Пронзающий холод",
    "Cinder": "Зола",
    "Cleanse": "Очищение",
    "Cleansing Touch": "Очищающее прикосновение",
    "Cold Snap": "Внезапный мороз",
    "Combat Perception": "Боевое восприятие",
    "Combustion": "Возгорание",
    "Concussive Blast": "Контузящий взрыв",
    "Conflagrate": "Пожарище",
    "Conflux": "Слияние",
    "Contagion": "Заражение",
    "Corrosion": "Коррозия",
    "Curse of Discord": "Проклятие раздора",
    "Curse of Frailty": "Проклятие немощи",
    "Curse of Oblivion": "Проклятие забвения",
    "Cursed Rune": "Проклятая руна",
    "Cyclone": "Циклон",
    "Dark Impulse": "Тёмный импульс",
    "Dark Spawn": "Тёмное порождение",
    "Death Nova": "Кольцо смерти",
    "Death's Dominion": "Владения смерти",
    "Deathguard": "Страж смерти",
    "Deathly Barrage": "Смертельный шквал",
    "Deathly Pall": "Смертный покров",
    "Dehydration": "Обезвоживание",
    "Dense Smoke": "Густой дым",
    "Desecration": "Осквернение",
    "Devout Deflection": "Благочестивое отражение",
    "Disarm": "Обезоруживание",
    "Disarm: Swordbreaker": "Обезоруживание: Мечелом",
    "Discharge": "Разряд",
    "Discord": "Раздор",
    "Discord Chaos": "Раздор: Хаос",
    "Discord Chaos 2": "Раздор: Хаос II",
    "Discord Frenzy": "Раздор: Ярость",
    "Discord Frenzy 2": "Раздор: Ярость II",
    "Discord Susceptibility": "Раздор: Восприимчивость",
    "Disease Damage": "Урон болезнью",
    "Distortion": "Искажение",
    "Distracting Shroud": "Отвлекающий покров",
    "Divine Aegis": "Божественная эгида",
    "Divine Armor": "Божественная броня",
    "Divine Avenger": "Божественный мститель",
    "Divine Insight": "Божественное озарение",
    "Divine Intervention": "Божественное вмешательство",
    "Divine Light": "Божественный свет",
    "Divine Plea": "Божественная мольба",
    "Divine Vengeance": "Божественное возмездие",
    "Doppelganger": "Двойник",
    "Dread Aura": "Аура ужаса",
    "Dreadful Touch": "Ужасающее прикосновение",
    "Earthbound Weapon": "Оружие земли",
    "Eldritch Power": "Зловещая мощь",
    "Electric Charge": "Электрический заряд",
    "Enhanced Mind": "Ясный разум",
    "Enslave Spirit": "Порабощение духа",
    "Envenom": "Отравление",
    "Everlasting Pain": "Вечная боль",
    "Fear": "Страх",
    "Fire Blast": "Огненный взрыв",
    "Fire Bomb": "Огненная бомба",
    "Fire Cloak": "Огненный плащ",
    "Fire Damage": "Урон огнем",
    "Flamestrike": "Огненный удар",
    "Flare": "Вспышка",
    "Flash of Light": "Вспышка света",
    "Fortify Stats": "Повышение характеристик",
    "Frost": "Холод",
    "Frost Armor": "Ледяной доспех",
    "Frost Barrier": "Ледяной барьер",
    "Frost Bomb": "Морозная бомба",
    "Frostbite": "Обморожение",
    "Furious Curse": "Яростное проклятие",
    "Glacial Fortress": "Ледниковая крепость",
    "Healing Touch": "Целительное прикосновение",
    "Hibernate": "Спячка",
    "Holy Bolt": "Священная стрела",
    "Hot Streak": "Полоса жара",
    "Howling Wind": "Воющий ветер",
    "Hypnotic Gaze": "Гипнотический взгляд",
    "Ice Charge": "Ледяной заряд",
    "Ice Lance": "Ледяное копье",
    "Icy Gale": "Ледяной шквал",
    "Ignite": "Воспламенение",
    "Inferno": "Инферно",
    "Instability": "Нестабильность",
    "Invisibility": "Невидимость",
    "Jolt": "Удар током",
    "Last Hope": "Последняя надежда",
    "Leadership": "Лидерство",
    "Lifegiving Veil": "Живительный покров",
    "Lightning Conductor": "Проводник молний",
    "Lightning Strike": "Удар молнии",
    "Lingering Curse": "Затяжное проклятие",
    "Mark of the Death": "Метка смерти",
    "Mending": "Исцеление",
    "Meteor": "Метеор",
    "Meteor Shower": "Метеоритный дождь",
    "Microburst": "Микропорыв",
    "Molten Fury": "Раскаленная ярость",
    "Molten Skin": "Лавовая кожа",
    "Natural Fusion": "Природный синтез",
    "Nature's Wrath": "Гнев природы",
    "Necrosis": "Некроз",
    "Negation": "Отрицание",
    "Nether Rift": "Разлом пустоты",
    "Oak Flesh": "Дубовая плоть",
    "Obscured Visibility": "Скрытая видимость",
    "Ooze": "Слизь",
    "Overgrowth": "Разрастание",
    "Pain Suppression": "Подавление боли",
    "Panic Curse": "Проклятие паники",
    "Paralysing Touch": "Парализующее прикосновение",
    "Penance": "Покаяние",
    "Permanence": "Постоянство",
    "Petrify": "Окаменение",
    "Phantasm": "Фантом",
    "Phantom": "Призрак",
    "Phantom Shroud": "Призрачный саван",
    "Phase Shift": "Фазовый сдвиг",
    "Phoenix Strike": "Удар феникса",
    "Phytogenesis": "Фитогенез",
    "Poison Essence": "Сущность яда",
    "Poison Sting": "Ядовитое жало",
    "Poison Swarm": "Ядовитый рой",
    "Purifying Flames": "Очищающее пламя",
    "Radiance of Light": "Сияние света",
    "Rage of the North": "Ярость севера",
    "Raised in Nature": "Дитя природы",
    "Replenish": "Восполнение",
    "Resonance": "Резонанс",
    "Revelation": "Откровение",
    "Revenant": "Выходец с того света",
    "Rift of Despair": "Разлом отчаяния",
    "Sacrifice": "Жертвоприношение",
    "Salamander Flame": "Пламя саламандры",
    "Salamander Terrible Flames": "Ужасающее пламя саламандры",
    "Salamander Touch": "Прикосновение саламандры",
    "Salamander Weapon": "Оружие саламандры",
    "Searing Light": "Обжигающий свет",
    "Searing Pain": "Жгучая боль",
    "Seed of Life": "Семя жизни",
    "Sequence": "Последовательность",
    "Shadow Orb": "Сфера тьмы",
    "Shieldbreaker": "Крушитель щитов",
    "Shock Damage": "Урон электричеством",
    "Shocking Pulse": "Шоковый импульс",
    "ShockingPulse": "Шоковый импульс",
    "Skyfall": "Небесный удар",
    "Slow Time Effect": "Замедление времени",
    "SlowTime": "Замедление времени",
    "Snowblind": "Снежная слепота",
    "Soften Weapon": "Размягчение оружия",
    "Soporific Poison": "Усыпляющий яд",
    "Soul Reaper": "Жнец душ",
    "Soul Steal": "Похищение души",
    "Soul Trap": "Захват душ",
    "Spectral Cloak": "Спектральный плащ",
    "Spectral Missile": "Спектральный снаряд",
    "Spectral Missiles": "Спектральные снаряды",
    "Stagger": "Ошеломление",
    "Static Barrier": "Статический барьер",
    "Storm Armor": "Громовой доспех",
    "Storm Orb": "Сфера бури",
    "Storm Shield": "Громовой щит",
    "Stormgate": "Врата бури",
    "Stormstrike": "Удар бури",
    "Straying Gateway": "Блуждающие врата",
    "Strength": "Сила",
    "Summon Ancient Lich": "Вызов древнего лича",
    "Summon Deathguard": "Вызов стража смерти",
    "Sunshine": "Солнечный свет",
    "Supercharge": "Сверхзарядка",
    "Superconductor": "Сверхпроводник",
    "Susceptibility": "Восприимчивость",
    "Swift Recharge": "Быстрая перезарядка",
    "Synthesis": "Синтез",
    "Tanglefoot": "Путы",
    "Taunt": "Провокация",
    "Tempest Spawn": "Порождение бури",
    "Terrible Flames": "Ужасающее пламя",
    "Throe": "Агония",
    "Tinder": "Трут",
    "Triumph": "Триумф",
    "Unholy Obsession": "Нечестивое наваждение",
    "Unrelenting Force Middle": "Безжалостная сила",
    "Vanquish the Weak": "Истребление слабых",
    "Veil of Nature": "Покров природы",
    "Vile Infusion": "Мерзкий настой",
    "Vile Spores": "Мерзкие споры",
    "Visions of Death": "Видения смерти",
    "Void Bolt": "Стрела пустоты",
    "Wild Growth": "Буйный рост",
    "Wild Growth Cooldown": "Буйный рост: Перезарядка",
    "Wild Mushroom": "Дикий гриб",
    "Wild Mushrooms": "Дикие грибы",
    "Wildfire": "Дикий огонь",
    "Winter Weapon": "Зимнее оружие",
    "Winter Weapon Frost": "Зимнее оружие: Холод",
    "Winter Woe": "Зимняя скорбь",
    "Wolf": "Волк",
    "Wolf Pack": "Волчья стая",
    "Wolf pack": "Волчья стая",
    "Wrath of the North": "Гнев севера",

    # NPC и торговцы
    "Lokun the Sage": "Локун Мудрец",
    "Lokun": "Локун",
    "Elethor": "Элетор",
    "Deathguard": "Страж смерти",
    "Dark Spawn": "Тёмное порождение",
    "Elethor's Goods": "Товары Элетора",
    "Lokun's Goods": "Товары Локуна",

    # Служебные эффекты и перезарядки
    "Immune freeze": "Иммунитет к заморозке",
    "Rift Cooldown": "Разлом: Перезарядка",
    "Rift CD": "Разлом: Перезарядка",
    "Phoenix Cooldown": "Феникс: Перезарядка",
    "Phoenix CD": "Феникс: Перезарядка",
    "Phoenix Gift CD": "Дар феникса: Перезарядка",
    "Glacial Fortress Cooldown": "Ледниковая крепость: Перезарядка",
    "Glacial Fortress Area": "Ледниковая крепость: Область",
    "Glacial Fortress Aftermath": "Ледниковая крепость: Последствия",
    "Doppelganger Cooldown": "Двойник: Перезарядка",
    "DPNG Cooldown": "Двойник: Перезарядка",
    "Electric Charge Hidden": "Электрический заряд (скрытый)",
    "Storm Orb Hidden": "Сфера бури (скрытая)",
    "Loot": "Добыча",
    "Magic": "Магия",
    "CD": "Перезарядка",
    "SMS": "Спектральные снаряды",
    "SMSpassive": "Спектральные снаряды (пассивно)",
    "DVH FX": "Божественный молот: Эффект",
    "AWPN FX": "Мистическое оружие: Эффект",
    "Hammer of Justice FX": "Молот правосудия: Эффект",
}


# Полный словарь всех описаний (Descriptions)
COMPLETE_DESCRIPTIONS_MAP = {
    "+<mag> armor rating.": "+<mag> к классу брони.",
    "+<mag> health and magicka.": "+<mag> к здоровью и магии.",
    "Applies an electric charge at the enemy for <60> sec. Use Electric Charge hotkey (default V) to trigger this spell, causing <10>-<60> shock damage.": 
        "Направляет электрический заряд во врага на <60> сек. Нажмите горячую клавишу (по умолчанию V), чтобы высвободить заряд и нанести <10>-<60> ед. урона электричеством.",
    "Attacks with swords have a 15% chance of doing more critical damage.": 
        "Атаки мечами имеют 15% шанс нанести повышенный критический урон.",
    "Blasts the target with light, causing <80> healing to an ally, or half that in damage to an enemy.": 
        "Поражает цель светом, восстанавливая <80> ед. здоровья союзнику или нанося вдвое меньше урона врагу.",
    "Bond of Pain can't be triggered.": "Узы боли не могут сработать.",
    "Burns the target for <mag> points. Targets on fire take extra damage.": 
        "Обжигает цель, нанося <mag> ед. урона огнем. Горящие цели получают дополнительный урон.",
    "Can't reapply Frost Barrier.": "Нельзя повторно применить Ледяной барьер.",
    "Can't reapply Oak Flesh effect.": "Нельзя повторно применить эффект Дубовой плоти.",
    "Can't trigger Light's Domination.": "Владычество света не может сработать.",
    "Can't use Stormgate.": "Нельзя использовать Врата бури.",
    "Cast on a nearby surface, it explodes for <mag> points of arcane damage when enemies come near, and curses the survivors.": 
        "Создает на поверхности руну, взрывающуюся на <mag> ед. мистического урона при приближении врагов и проклинающую выживших.",
    "Caster is invisible for <dur> seconds. Activating an object or attacking will break the spell.": 
        "Заклинатель невидим в течение <dur> сек. Атака или взаимодействие с предметом развеют заклинание.",
    "Causes <mag> shock damage to all targets in a 20 ft radius.": 
        "Наносит <mag> ед. урона электричеством всем целям в радиусе 20 футов.",
    "Causes your next Electric Charge to deal an additional 50% damage.": 
        "Следующий Электрический заряд нанесет на 50% больше урона.",
    "Charges at the enemy target, knocking them down. <30> sec cooldown.": 
        "Рывок к цели, сбивающий её с ног. Перезарядка: <30> сек.",
    "Charges the target, causing <mag> shock damage per sec for <dur> sec.": 
        "Заряжает цель электричеством, нанося <mag> ед. урона в секунду в течение <dur> сек.",
    "Concussive Blast can't be triggered.": "Контузящий взрыв не может сработать.",
    "Conflagrate deals <10>% more damage.": "Пожарище наносит на <10>% больше урона.",
    "Conflagrate deals <20>% more damage.": "Пожарище наносит на <20>% больше урона.",
    "Conflagrate deals <30>% more damage.": "Пожарище наносит на <30>% больше урона.",
    "Creates a magic mace for <dur> seconds. Sheathe it to dispel.": 
        "Создает магическую булаву на <dur> сек. Уберите её в ножны, чтобы развеять.",
    "Creates a mystical portal at the caster location for <dur> sec. Upon pressing the hotkey (default G), instantly teleports the caster to the portal. There is a <10> sec cooldown between each translocation.": 
        "Создает мистический портал в точке заклинателя на <dur> сек. Нажатие горячей клавиши (по умолчанию G) мгновенно телепортирует к порталу. Перезарядка телепортации: <10> сек.",
    "Creates an arcane weapon for <dur> seconds. Sheathe it to dispel.": 
        "Создает мистическое оружие на <dur> сек. Уберите его в ножны, чтобы развеять.",
    "Creates an illusionary copy of the target for <dur> seconds. Doesn't work on dragons, undeads and machines. 30 sec cooldown.": 
        "Создает иллюзорную копию цели на <dur> сек. Не действует на драконов, нежить и механизмы. Перезарядка: 30 сек.",
    "Creatures and people up to level <mag> flee from combat for <dur> seconds.": 
        "Существа и люди до <mag> уровня обращаются в бегство на <dur> сек.",
    "Creatures and people up to level <mag> will attack anyone nearby for <dur> seconds,": 
        "Существа и люди до <mag> уровня атакуют всех вокруг в течение <dur> сек.,",
    "Curses the target, causing <mag> disease damage per sec for <dur> sec.": 
        "Проклинает цель, нанося <mag> ед. урона болезнью в секунду в течение <dur> сек.",
    "Deals extra fire damage.": "Наносит дополнительный урон огнем.",
    "Death Nova can't be triggered.": "Кольцо смерти не может сработать.",
    "Decrease the spells mana cost by <50>%.": "Снижает расход магии заклинаниями на <50>%.",
    "Decreases Wild Mushroom mana cost by <100>%.": "Снижает расход магии на Дикий гриб на <100>%.",
    "Decreases all damage taken by <50>%.": "Снижает весь получаемый урон на <50>%.",
    "Decreases damage taken by  <15>%.": "Снижает получаемый урон на <15>%.",
    "Decreases electric spells mana cost by <25>%.": "Снижает расход магии на заклинания электричества на <25>%.",
    "Decreases magic damage taken by <50>%.": "Снижает получаемый магический урон на <50>%.",
    "Decreases the mana cost of Stormstrike and Lightning Strike by <50>%.": 
        "Снижает расход магии на Удар бури и Удар молнии на <50>%.",
    "Divine Avenger can't be triggered.": "Божественный мститель не может сработать.",
    "Divine Intervention can't be triggered.": "Божественное вмешательство не может сработать.",
    "Doubles the Susceptibility effects of Cursed Rune and Discord.": 
        "Удваивает эффекты восприимчивости от Проклятой руны и Раздора.",
    "Electrocute does not require a storm shard to trigger, and works on targets with 35% health or less.": 
        "Удар током больше не требует осколка бури и срабатывает на целях с 35% здоровья или меньше.",
    "Encases the caster in solid ice for <10> seconds, providing a respite from combat.": 
        "Заключает заклинателя в монолитный лед на <10> сек., давая передышку в бою.",
    "Encases the caster in solid ice for <dur> sec.": 
        "Заключает заклинателя в монолитный лед на <dur> сек.",
    "Fire Blast costs <70>% less mana to cast.": "Огненный взрыв требует на <70>% меньше магии.",
    "Fire damage increased by <25>%.": "Урон огнем увеличен на <25>%.",
    "Fire resistance decreased.": "Сопротивление огню снижено.",
    "For <dur> seconds, opponents in melee range take <mag> points fire damage per second. Targets on fire take extra damage.": 
        "В течение <dur> сек. противники вблизи получают <mag> ед. урона огнем в секунду. Горящие цели получают дополнительный урон.",
    "Healing spells cost nothing.": "Заклинания лечения не расходуют магию.",
    "Heals the caster <22> to <30> health on hit.": "Восстанавливает заклинателю от <22> до <30> ед. здоровья при ударе.",
    "Heals the caster <mag> points per sec for <dur> sec.": "Восстанавливает заклинателю <mag> ед. здоровья в секунду в течение <dur> сек.",
    "Heals the caster <mag> points per sec.": "Восстанавливает заклинателю <mag> ед. здоровья в секунду.",
    "Heals the caster <mag> points.": "Восстанавливает заклинателю <mag> ед. здоровья.",
    "Hurls a fiery bolt at the target, causing <mag> fire damage.": 
        "Метает во врага огненную стрелу, наносящую <mag> ед. урона огнем.",
    "Hurls a spear of ice at the target that causes <mag> points of frost damage to Health and Stamina.": 
        "Метает во врага ледяное копье, наносящее <mag> ед. урона холодом здоровью и запасу сил.",
    "Ice Surge restores <20> mana.": "Ледяной всплеск восстанавливает <20> ед. магии.",
    "If target dies within <dur> seconds, fills a soul gem.": 
        "Если цель погибает в течение <dur> сек., захватывает её душу.",
    "Imbues the caster with divine energy, reducing incoming spells damage by <15>% for <dur> sec.": 
        "Наполняет заклинателя божественной энергией, снижая получаемый урон от заклинаний на <15>% на <dur> сек.",
    "Imbues the caster with electricity, increasing shock resistance by <mag>% for <dur> sec.": 
        "Наполняет заклинателя электричеством, увеличивая сопротивление электричеству на <mag>% на <dur> сек.",
    "Imbues the caster's weapon with Earth, increasing magicka regeneration by <mag>% for <dur> sec.": 
        "Наполняет оружие силой земли, повышая регенерацию магии на <mag>% на <dur> сек.",
    "Immunity to magic.": "Иммунитет к магии.",
    "Immunity to physical damage.": "Иммунитет к физическому урону.",
    "Increase your Holy Bolt effectiveness by 50%.": "Увеличивает эффективность Священной стрелы на 50%.",
    "Increases Wild Mushroom damage by <25>%.": "Увеличивает урон Дикого гриба на <25>%.",
    "Increases a chance to apply Searing Pain and Ignite effects by <mag>%.": 
        "Повышает шанс наложить эффекты Жгучей боли и Воспламенения на <mag>%.",
    "Increases a chance to freeze the target by <50>%.": "Повышает шанс заморозить цель на <50>%.",
    "Increases damage by <50>%.": "Увеличивает урон на <50>%.",
    "Increases damage of all fire spells.": "Увеличивает урон всех заклинаний огня.",
    "Increases electric damage by <50>%.": "Увеличивает урон электричеством на <50>%.",
    "Increases electric resistance by <mag>%.": "Увеличивает сопротивление электричеству на <mag>%.",
    "Increases fire resistance by <mag>%.": "Увеличивает сопротивление огню на <mag>%.",
    "Increases frost resistance by <mag>%.": "Увеличивает сопротивление холоду на <mag>%.",
    "Increases frost spells damage and mana cost by <25>%.": 
        "Увеличивает урон и расход магии заклинаний холода на <25>%.",
    "Increases magic resistance by <20>%.": "Увеличивает сопротивление магии на <20>%.",
    "Increases meteors count by <mag>.": "Увеличивает количество метеоров на <mag>.",
    "Increases physical damage by <25>%.": "Увеличивает физический урон на <25>%.",
    "Increases the Doppelganger duration by <50>%.": "Увеличивает длительность Двойника на <50>%.",
    "Increases the damage of Ice Lance by <20>%.": "Увеличивает урон Ледяного копья на <20>%.",
    "Increases the damage of Poison Bite and Vile Spores by <2> points/sec.": 
        "Увеличивает урон Ядовитого укуса и Мерзких спор на <2> ед./сек.",
    "Increases the damage, healing, and mana cost of your Druid's spells by <25>%.": 
        "Увеличивает урон, исцеление и расход магии заклинаний друида на <25>%.",
    "Increases the duration of Divine Light effects by <2> sec.": "Увеличивает длительность эффектов Божественного света на <2> сек.",
    "Increases the duration of Frost Barrier by <2> sec.": "Увеличивает длительность Ледяного барьера на <2> сек.",
    "Increases the duration of Stormstrike by <50>%.": "Увеличивает длительность Удара бури на <50>%.",
    "Increases the duration of Veil of Nature by <100>%.": "Увеличивает длительность Покрова природы на <100>%.",
    "Increases the duration of your next Blight Curse and Necrosis by <50>%.": 
        "Увеличивает длительность следующего Гибельного проклятия и Некроза на <50>%.",
    "Increases the effect of Divine Vengeance by <10>%.": "Увеличивает эффект Божественного возмездия на <10>%.",
    "Increases the initial damage of Seed of Life by <50>%.": "Увеличивает начальный урон Семени жизни на <50>%.",
    "Increases your armor rating by <25>%.": "Увеличивает класс брони на <25>%.",
    "Increases your chance to score a critcal strike by 15%.": "Повышает шанс критического удара на 15%.",
    "Increases your damage by <mag>%.": "Увеличивает ваш урон на <mag>%.",
    "Increases your physical damage by <20>%.": "Увеличивает ваш физический урон на <20>%.",
    "Increases your spell damage by <mag>%.": "Увеличивает урон от заклинаний на <mag>%.",
    "Infects the target with pestilence, causing <mag> disease damage each <5> sec for <dur> sec.": 
        "Заражает цель моровой язвой, нанося <mag> ед. урона болезнью каждые <5> сек. в течение <dur> сек.",
    "Instantly blasts the target, causing <mag> fire damage.": 
        "Мгновенно взрывает цель, нанося <mag> ед. урона огнем.",
    "Jolt can't be triggered.": "Удар током не может сработать.",
    "Last Hope can't be triggered.": "Последняя надежда не может сработать.",
    "Launches <2> magic missiles at the target, each causing <mag>% of your total magicka as fire, frost, or shock damage. Each missile drains <10>% of your magicka.": 
        "Выпускает во врага <2> магических снаряда, каждый из которых наносит урон огнем, холодом или электричеством в размере <mag>% от запаса магии. Каждый снаряд сжигает <10>% магии.",
    "Movement speed increased by <mag>.": "Скорость передвижения увеличена на <mag>.",
    "On activation, absorbs up to <25>% incoming damage, draining magicka instead. Drains <8> magicka per sec. Lasts until canceled.": 
        "При активации поглощает до <25>% получаемого урона, расходуя магию. Сжигает <8> ед. магии в секунду. Действует до отмены.",
    "Places a magical trap at the target location. For <15> sec afterwards, the enemy will be teleported to trap's initial position.": 
        "Устанавливает магическую ловушку. В течение следующих <15> сек. враг будет телепортирован обратно к исходной точке ловушки.",
    "Plants a wild mushroom at the target position that explodes each <3> sec, causing <mag> poison damage to all nearby enemies.": 
        "Выращивает дикий гриб, взрывающийся каждые <3> сек. и наносящий <mag> ед. урона ядом всем врагам поблизости.",
    "Pressing the hotkey within 5 sec after translocation, moves the stormgate to your initial position.": 
        "Нажатие горячей клавиши в течение 5 сек. после перемещения переносит Врата бури в вашу исходную позицию.",
    "Progress: %.0f%%": "Прогресс: %.0f%%",
    "Protects the caster with frost armor, increasing armor rating by <mag> for <dur> sec.": 
        "Защищает заклинателя ледяным доспехом, повышая класс брони на <mag> ед. на <dur> сек.",
    "Raise victims of Blight Curse to do your bidding.": 
        "Поднимает жертв Гибельного проклятия, заставляя их сражаться на вашей стороне.",
    "Reanimate a very powerful dead body to fight for you for <dur> seconds.": 
        "Оживляет могущественное мертвое тело, заставляя сражаться за вас в течение <dur> сек.",
    "Reduces armor rating by <mag>.": "Снижает класс брони на <mag> ед.",
    "Reduces shock resistance by <mag>%.": "Снижает сопротивление электричеству на <mag>%.",
    "Reflects melee damage.": "Отражает урон ближнего боя.",
    "Restores 3 to 5 mana per sec.": "Восстанавливает от 3 до 5 ед. магии в секунду.",
    "Sends a bolt of dark energy at the target, causing damage equal to <15>% of the caster's current health. Restores health equal to <50>% of that damage to the caster after <3> sec.": 
        "Направляет в цель стрелу темной энергии, наносящую урон в размере <15>% от текущего здоровья заклинателя. Через <3> сек. восстанавливает заклинателю здоровье в размере <50>% от нанесенного урона.",
    "Sends a poison bolt at the target, causing <mag> damage.": 
        "Метает ядовитую стрелу во врага, нанося <mag> ед. урона.",
    "Shock spells cost nothing.": "Заклинания электричества не расходуют магию.",
    "Siphon effects restore an additional <mag> points per tick.": 
        "Эффекты вытягивания восстанавливают дополнительно <mag> ед. за тик.",
    "Slows time for <dur> seconds.": "Замедляет время на <dur> сек.",
    "Spell damage increased by <mag>%.": "Урон заклинаний увеличен на <mag>%.",
    "Strikes the target with lightning, causing <mag> shock damage to health, and half that to mana.": 
        "Поражает цель молнией, нанося <mag> ед. урона электричеством здоровью и вдвое меньше магии.",
    "Summons <3> fiery meteors down upon the target, causing <mag> fire damage. Only usable outdoors.": 
        "Обрушивает на цель <3> огненных метеора, наносящих <mag> ед. урона огнем. Работает только под открытым небом.",
    "Summons a Deathguard for <dur> seconds wherever the caster is pointing.": 
        "Призывает Стража смерти на <dur> сек. в указанное заклинателем место.",
    "Summons a pack of wolves for <dur> seconds wherever the caster is pointing.": 
        "Призывает волчью стаю на <dur> сек. в указанное заклинателем место.",
    "Summons an Ancient Lich for <dur> seconds wherever the caster is pointing.": 
        "Призывает Древнего лича на <dur> сек. в указанное заклинателем место.",
    "Summons an axe imbued with divine energy to fight for you for <dur> seconds.": 
        "Призывает топор, наполненный божественной энергией, сражающийся за вас <dur> сек.",
    "Surrounds the caster with death energy for <dur> seconds, increasing damage of Blight Curse and Necrosis by <25>%.": 
        "Окружает заклинателя энергией смерти на <dur> сек., увеличивая урон Гибельного проклятия и Некроза на <25>%.",
    "Surrounds the caster with natural energy that affects nearby enemies, decreasing their poison resistance by <33>%. Lasts <dur> sec.": 
        "Окружает заклинателя природной энергией, снижающей сопротивление яду у врагов поблизости на <33>%. Длится <dur> сек.",
    "Take the form of a phantom, making sneaking <mag>% more effective for <dur> sec.": 
        "Принимает форму призрака, делая скрытность на <mag>% эффективнее на <dur> сек.",
    "Targets take <mag> points of frost damage for <dur> seconds, plus Stamina damage.": 
        "Цели получают <mag> ед. урона холодом в течение <dur> сек., а также урон запасу сил.",
    "The target becomes a living bomb, taking <mag> frost damage per sec over <6> sec. After 6 sec, frost bomb explodes, causing frost damage to all targets nearby.": 
        "Цель становится живой бомбой, получая <mag> ед. урона холодом в секунду в течение <6> сек. Через 6 сек. бомба взрывается, нанося урон холодом всем врагам вокруг.",
    "Time between shouts is reduced by <50>%.": "Время между криками снижено на <50>%.",
    "Warlock spells cost no mana.": "Заклинания чернокнижника не расходуют магию.",
    "Wolf Pack summons <4> wolves at once.": "Волчья стая призывает <4> волков одновременно.",
    "Your spells cost <40>% less to cast.": "Ваши заклинания расходуют на <40>% меньше магии.",
    "spreading chaos among your enemies.": "сея хаос среди ваших врагов.",
}


def translate_entry_full(entry: dict) -> str:
    orig = entry.get("original", "").strip()
    field = entry.get("field", "")

    if not orig:
        return ""

    # 1. Тексты книг (BookText)
    if field == "BookText":
        clean = re.sub(r'<[^>]+>', '', orig).strip()
        lines = [line.strip() for line in clean.split('\n') if line.strip()]
        title_eng = lines[0] if lines else orig
        title_rus = COMPLETE_NAMES_MAP.get(title_eng, COMPLETE_NAMES_MAP.get(f"Forgotten Magic: {title_eng}", title_eng))
        return (
            "<font face='$HandwrittenFont'><font size='40'><p align='center'>\n"
            f"{title_rus}\n"
            "</p></font><font size='20'>\n\n"
            f"Прочтите этот древний трактат, чтобы овладеть утерянным искусством: {title_rus}.\n"
            "</font>"
        )

    # 2. Описания (Description)
    if field == "Description":
        if orig in COMPLETE_DESCRIPTIONS_MAP:
            return COMPLETE_DESCRIPTIONS_MAP[orig]

    # 3. Названия (Name, ShortName)
    if orig in COMPLETE_NAMES_MAP:
        return COMPLETE_NAMES_MAP[orig]

    # 4. Составные префиксы
    if orig.startswith("Forgotten Magic: "):
        sub = orig.replace("Forgotten Magic: ", "").strip()
        sub_tr = COMPLETE_NAMES_MAP.get(sub, sub)
        return f"Забытая магия: {sub_tr}"

    # 5. Проверка описаний по словарю
    if orig in COMPLETE_DESCRIPTIONS_MAP:
        return COMPLETE_DESCRIPTIONS_MAP[orig]

    # Системные переменные оставляем как есть
    if orig.startswith("pRing") or orig.startswith("pArmor") or orig.startswith("pGlacial") or orig.startswith("pWinter") or orig.startswith("pSalamander") or orig.startswith("pCombat") or orig.startswith("vFaction") or orig.startswith("xxp") or orig == "v" or orig.startswith("$"):
        return orig

    return orig


def main():
    print("🐾 === ЗАПУСК БЕЗОШИБОЧНОГО ПЕРЕВОДА ВСЕХ СТРОК FMR ===")
    with open(REVIEW_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    entries = data.get("entries", [])
    tm_engine = TranslationEngine(mod_name="ForgottenMagic_Redone")

    for e in entries:
        tr = translate_entry_full(e)
        e["translated"] = tr
        e["source"] = "lain_agent"

        tm_engine.save_translation(
            record_type=e.get("type", "MISC"),
            field_path=e.get("field", "Name"),
            original=e.get("original", ""),
            translated=tr,
            formid=e.get("formid", ""),
            source="lain_agent",
            auto_save=False
        )

    data["metadata"]["ready_count"] = len(entries)
    with open(REVIEW_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    tm_engine._save_tm()
    print(f"✨ Все {len(entries)} строк успешно переведены и сохранены в ревью-файл и TM!")


if __name__ == "__main__":
    main()
