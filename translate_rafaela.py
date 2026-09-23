"""
Полный перевод всех 110 строк Rafaela.esp (включая NPC, книги, диалоги, крики, эффекты, заклинания, расы, броню и оружие).
"""

import json
from pathlib import Path
from src.review_manager import ReviewManager
from src.translation import TranslationEngine, normalize_mod_name
from src.quality_gate import QualityGate

RAFAELA_TRANSLATIONS = {
    # NPC
    "Rafaela": "Рафаэла",
    "0SummonAngel": "Призванный ангел",
    "Summoned Angel": "Призванный ангел",
    
    # Dialogues
    "Could you show that pretty little body of yours?": "Не покажешь ли ты свое прелестное тело?",
    "Let me think about it...": "Дай мне подумать об этом...",
    "Could you show that pretty little angel body of yours?": "Не покажешь ли ты свое прелестное ангельское тело?",
    "Could you show that heavenly body of yours?": "Не покажешь ли ты свое божественное тело?",
    "Really? So... can I turn back into my true form?": "Правда? Значит... я могу вернуться в свой истинный облик?",
    "Could you transform back to your human form?": "Не могла бы ты вернуться в свой человеческий облик?",
    "Dress like a normal kid, but be ready for battle.": "Оденься как обычный ребенок, но будь готова к битве.",
    "Wow! This armor is really cool!": "Ого! Эти доспехи просто класс!",
    
    # Books & Spells
    "Summons an Angel": "Призывает ангела",
    "<font face'$HandwrittenFont'><font size='40'><p align='center'>Summons an Angel": "<font face'$HandwrittenFont'><font size='40'><p align='center'>Призывает ангела",
    "<font face'$HandwrittenFont'><font size='40'><p align='center'>Holy Light to smite the unworthy": "<font face'$HandwrittenFont'><font size='40'><p align='center'>Священный свет для сокрушения недостойных",
    "<font face'$HandwrittenFont'><font size='40'><p align='center'>\r\nWrath of Heavens smite the unworthy": "<font face'$HandwrittenFont'><font size='40'><p align='center'>\r\nГнев небес сокрушает недостойных",
    "Spell : Summon Angel": "Заклинание: Призыв ангела",
    "Summon Angel Spell": "Заклинание призыва ангела",
    "Spell : Sun Beam": "Заклинание: Солнечный луч",
    "Spell : Sun Beam (Expert)": "Заклинание: Солнечный луч (Эксперт)",
    "Sun Beam": "Солнечный луч",
    "Sun Beam (Expert)": "Солнечный луч (Эксперт)",
    "Spell Tome: Holy Light": "Том заклинаний: Священный свет",
    "Spell Tome: Wrath of Heavens": "Том заклинаний: Гнев небес",
    "Forces enemies to flee in terror": "Заставляет врагов в ужасе бежать",
    "Heals the caster and nearby allies": "Исцеляет заклинателя и ближайших союзников",
    "Greatly heals the caster": "Значительно исцеляет заклинателя",
    "Pushes away all targets in front of you": "Отбрасывает все цели перед вами",
    "Holy Light": "Священный свет",
    "Wrath of Heavens": "Гнев небес",
    "Rafaela Heal Spell": "Заклинание исцеления Рафаэлы",
    "Rafi's Healing Touch": "Исцеляющее прикосновение Рафи",
    "Rafi Healing Touch": "Исцеляющее прикосновение Рафи",
    "ForcePush": "Силовой толчок",
    
    # Shouts
    "Rafaela Shout": "Крик Рафаэлы",
    "Rafi's Healing": "Исцеление Рафи",
    "RafiHealing": "Исцеление Рафи",
    "Force Push": "Силовой толчок",
    "ForceShout": "Крик силы",
    "Call Angel": "Призыв ангела",
    "CallAngel": "Призыв ангела",
    "You receive Keiko's healing touch.": "Вы получаете исцеляющее прикосновение Кейко.",
    "Keiko's voice is raw power, pushing aside anything - or anyone - who stands in her path.": "Голос Кейко — первозданная мощь, сметающая все и вся на её пути.",
    "Summons an Angel from heavens.": "Призывает ангела с небес.",
    "Summons an Angel from heavens": "Призывает ангела с небес",
    
    # Armor & Clothing
    "Angel Lesser Wings": "Малые ангельские крылья",
    "Angelic Set": "Ангельский комплект",
    "Casual Dress Set": "Комплект повседневного платья",
    "특수 이펙트 효과": "Особый визуальный эффект",
    "Peace Gem Simple": "Простой самоцвет мира",
    "Angel Amulet": "Ангельский амулет",
    "Angel Hair": "Ангельская прическа",
    "Heavenly Seal": "Небесная печать",
    "Angel Gauntlets": "Ангельские перчатки",
    "Angel Skirt": "Ангельская юбка",
    "Angel Helmet": "Ангельский шлем",
    "Angel Halo": "Ангельский нимб",
    "Bless the worthy ones with armor sent from heavens.": "Благословляет достойных доспехами, ниспосланными с небес.",
    "Ring of Divine Protection": "Кольцо божественной защиты",
    "Rafi's Wings": "Крылья Рафи",
    "Rafi's White Wig": "Белый парик Рафи",
    "Angel Wings": "Ангельские крылья",
    "Angelic Seals": "Ангельские печати",
    "Angel Inner Skirt": "Нижняя ангельская юбка",
    "Angel Pauldron": "Ангельский наплечник",
    "Angel Arm Guard": "Ангельские наручи",
    "Angel Boots": "Ангельские сапоги",
    "CF_NakedArmor": "CF_NakedArmor",
    "Handsewn by the famous artist 5chars.": "Сшито вручную знаменитым мастером 5chars.",
    "Casual Summer Dress": "Повседневное летнее платье",
    "Hand crafted by the famous artist 5chars.": "Создано вручную знаменитым мастером 5chars.",
    "Casual Straw Hat": "Повседневная соломенная шляпа",
    "Casual Necklace": "Повседневное ожерелье",
    "Casual Sandals": "Повседневные сандалии",
    "Casual Bracelet": "Повседневный браслет",
    "Imbues the worthy in heavenly light": "Озаряет достойного небесным светом",
    "Blessed Hairpin": "Благословенная шпилька",
    "Ring Of Facelight": "Кольцо подсветки лица",
    
    # Weapons
    "Angel Giant Greatsword": "Исполинский ангельский двуручный меч",
    "Summoned Angel's Greatsword": "Призванный ангельский двуручный меч",
    "Angelic Greatsword": "Ангельский двуручный меч",
    
    # Magic Effects, Perks, Enchantments & Races
    "Peace Silencer FX": "Эффект усмирения",
    "Angel Circle": "Ангельский круг",
    "Summon Angel": "Призыв ангела",
    "Angel Tri Circle": "Тройной ангельский круг",
    "Holy Light Effect": "Эффект священного света",
    "Wrath of Heavens Effect": "Эффект гнева небес",
    "Heavenly seal protect the wearer.": "Небесная печать защищает носителя.",
    "Angelic seals protect the wearer.": "Ангельские печати защищают носителя.",
    "Summons an Angel from heavens to smite evil for<dur>seconds": "Призывает ангела с небес для сокрушения зла на <dur> сек.",
    "Divine energy focused on a ray inflicts inflicts <mag> points of damage per second.": "Божественная энергия, сфокусированная в луч, наносит <mag> ед. урона в секунду.",
    "Divine energy explodes on impact, dealing <mag> points of damage in a 10 foot radius.": "Божественная энергия взрывается при попадании, нанося <mag> ед. урона в радиусе 10 футов.",
    "Summoned Angel Race": "Раса призванного ангела",
    "Summoned from heavens to smite evil.": "Призвана с небес для сокрушения зла.",
    "Custom Race": "Особая раса",
    "NordRace_CF": "Норд (CF)",
    "RafaelaClass": "Класс Рафаэлы",
    "Cornelia's Protection": "Защита Корнелии",
    "Protects the wearer with heavenly grace": "Защищает носителя небесной благодатью",
    "Facelight Effect": "Эффект подсветки лица",
    "FacelightEffect": "Эффект подсветки лица",
    "Summon Dragon Effect": "Эффект призыва дракона",
    "SummonDragonEffect": "Эффект призыва дракона",
    "Summonable Angel Effect": "Эффект призываемого ангела",
    "Summons a Familiar for <dur> seconds wherever the caster is pointing.": "Призывает питомца на <dur> сек. в точку, куда указывает заклинатель.",
    "Force Push Effect": "Эффект силового толчка",
    "ForcePushEffect": "Эффект силового толчка",
    "Rafaela Effect": "Эффект Рафаэлы",
    "Rafaela's Force Push Effect": "Эффект силового толчка Рафаэлы",
    "Keiko Healing Effect": "Эффект исцеления Кейко",
    "KeikoHealingEffect": "Эффект исцеления Кейко",
    "aaAlicesshouteffect": "Эффект крика Рафаэлы",
    "aaAlicesshouteffect2": "Эффект крика Рафаэлы II",
    "aaAlicesshouteffect3": "Эффект крика Рафаэлы III",
    "aaAlicesshouteffect4": "Эффект крика Рафаэлы IV",
    "outfitEffect01A": "Эффект наряда 01A",
    "outfitEffect01B": "Эффект наряда 01B",
    "0TomFreyjaSilencer": "Утишитель Фрейи",
    "Silencer": "Утишитель",
    "Smite the undead dealing an extra 50% damage.": "Сокрушает нежить, нанося дополнительно 50% урона.",
    "Rafaela Perk": "Способность Рафаэлы",
    "TransformInAngel": "Превращение в ангела",
    "Peace Simple Enchant": "Простое зачарование покоя",
    "Angelic Magic Circle": "Ангельский магический круг",
    "Angelic Magic Tri Circle": "Тройной ангельский магический круг",
    "Temple of Dibella": "Храм Дибеллы",
    "Temple of Kynareth": "Храм Кинарет",
}

def translate_all_rafaela():
    raw_path = Path("data/raw_extracted/Rafaela_raw.json")
    items = json.load(open(raw_path, encoding="utf-8"))
    
    clean_name = normalize_mod_name("Rafaela.esp")
    tm = TranslationEngine(mod_name=clean_name)
    
    for item in items:
        orig = item.get("text", "").strip()
        trans = RAFAELA_TRANSLATIONS.get(orig, orig)
        item["translated"] = trans
        item["source"] = "lain_agent"
        tm.save_translation(item.get("type", "MISC"), item.get("path", "Name"), orig, trans, item.get("formid", ""), source="lain_agent", auto_save=False)

    tm._save_tm()
    out_review = ReviewManager.export_for_review(clean_name, items)
    print(f"✅ Файл ревью сохранен ({len(items)} строк): {out_review}")
    
    # Аудит через Quality Gate
    reviewed = ReviewManager.load_reviewed_file(out_review)
    report = QualityGate.audit_entries(reviewed)
    print(report.summary())
    if report.issues:
        for i in report.issues:
            print(f"  • [{i.issue_type}] {i.formid} ({i.field}): {i.details}")

if __name__ == "__main__":
    translate_all_rafaela()
