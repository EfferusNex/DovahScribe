"""
Mapping of Skyrim Record Types to translatable field paths based on xTranslator and houseCARL (Mutagen) schema.
"""

FIELD_FILTERS = {
    # Actors and Items
    'ARMO': ['Name', 'Description'],
    'WEAP': ['Name', 'Description'],
    'MISC': ['Name', 'Description'],
    'ALCH': ['Name', 'Description'],
    'INGR': ['Name', 'Description'],
    'BOOK': ['Name', 'Description', 'BookText'],
    'AMMO': ['Name', 'Description'],
    'APPA': ['Name', 'Description'],
    'KEYM': ['Name', 'Description'],
    'SLGM': ['Name', 'Description'],
    'NPC_': ['Name', 'ShortName', 'Configuration.Flags', 'Race', 'Voice'],

    # Dialogues and Quests
    'DIAL': ['Name', 'Prompt'],
    'INFO': ['Prompt', 'Responses[*].Text', 'Speaker', 'Conditions', '*parent.Name', '*parent.EditorID'],
    'QUST': ['Name', 'Description', 'Objectives[*].DisplayText'],
    'SCEN': ['Name'],
    'MESG': ['Name', 'Description', 'MenuButtons[*].Text'],

    # Locations and World
    'CELL': ['Name'],
    'WRLD': ['Name'],
    'LCTN': ['Name'],
    'CONT': ['Name'],
    'DOOR': ['Name'],
    'FLOR': ['Name'],
    'TREE': ['Name'],
    'TACT': ['Name'],
    'ACTI': ['Name', 'ActivateTextOverride'],

    # Magic and Effects
    'SPEL': ['Name', 'Description'],
    'MGEF': ['Name', 'Description'],
    'ENCH': ['Name', 'Description'],
    'PERK': ['Name', 'Description'],
    'SHOU': ['Name', 'Description'],
    'FACT': ['Name', 'Description'],
    'CLAS': ['Name'],
    'RACE': ['Name', 'Description'],
    'AVIF': ['Name', 'Description'],
    'LSCR': ['Description'],
    'EXPL': ['Name'],
    'PROJ': ['Name'],
    'REFR': ['MapMarker.Name', 'Name'],
    'ACHR': ['Name'],
}

# Список всех отслеживаемых типов записей по умолчанию
ALL_SUPPORTED_TYPES = list(FIELD_FILTERS.keys())

def get_fields_for_record(record_type: str) -> list[str]:
    """Возвращает список транслируемых полей для указанного типа записи Skyrim."""
    return FIELD_FILTERS.get(record_type, ['Name', 'Description'])
