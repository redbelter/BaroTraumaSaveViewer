import dearpygui.dearpygui as dpg
import re

# Get all public callables from dpg
dpg_funcs = set()
for name in dir(dpg):
    if not name.startswith('_'):
        obj = getattr(dpg, name)
        if callable(obj) and not isinstance(obj, int):
            dpg_funcs.add(name)

# Read the file
with open(r'C:\Users\red\Desktop\code\reverse-baro\src\gui.py', encoding='utf-8') as f:
    lines = f.readlines()

# Find all dpg.function_name calls
dpg_calls = {}
for i, line in enumerate(lines, 1):
    for m in re.finditer(r'dpg\.(\w+)\(', line):
        dpg_calls.setdefault(m.group(1), []).append(i)

# Check each call
for name in sorted(dpg_calls):
    if name not in dpg_funcs:
        print(f'MISSING: {name} -> lines {dpg_calls[name]}')
    else:
        print(f'OK: {name}')
