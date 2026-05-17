import sys
sys.path.insert(0, "src")
from parser.data import item_type_from_identifier

# Test the one that failed
result = item_type_from_identifier("food_meat_cooked")
print("Result:", repr(result))
assert result == "meat", f"Expected 'meat', got {repr(result)}"
