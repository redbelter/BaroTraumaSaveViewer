import sys
sys.path.insert(0, 'src')
from parser.data import item_type_from_identifier

tests = [
    ("duffelbag_container", "duffelbag"),
    ("gun_shotgun", "shotgun"),
    ("food_meat_cooked", "meat"),
    ("customitem", "custom"),
]

for identifier, expected in tests:
    result = item_type_from_identifier(identifier)
    status = "OK" if result == expected else "FAIL"
    print("%s: %s (got '%s', expected '%s')" % (status, identifier, result, expected))
