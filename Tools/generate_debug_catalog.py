#!/usr/bin/env python3
"""Генерирует Scripts/DebugCatalog.fos — каталог прототипов предметов и локаций для дебаг-меню.

Источник: Items/*.foitem (тип и имя прототипа), Maps/*.foloc (локации и их субкарты). Идентификаторы
берутся из Scripts/Content.fos (namespace Item / Location / Map), чтобы опечатки ловились компилятором.
Файл нужен внутриигровому дебаг-меню (Scripts/DebugMenu.fos). Напрямую не редактировать —
перегенерировать после изменения набора прототипов.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


# Категории меню: имя массива в DebugCatalog.fos -> тип прототипа предмета.
CATEGORY_BY_TYPE = {
    'Weapon': 'Weapons',
    'Ammo': 'Ammo',
    'Armor': 'Armor',
    'Drug': 'Drugs',
    'Container': 'Containers',
    'Key': 'Keys',
    'Misc': 'Misc',
}

# Порядок массивов в файле (совпадает с порядком категорий в UI).
CATEGORY_ORDER = ['Weapons', 'Ammo', 'Armor', 'Drugs', 'Containers', 'Keys', 'Misc', 'Locations']

CONTENT_CONST_RE = re.compile(r'^\s*const hstring (\w+) = ".*"\.hstr\(\);', re.MULTILINE)


def read_text(path: Path) -> str:
    return path.read_bytes().decode('utf-8-sig')


def parse_field(content: str, name: str) -> str | None:
    match = re.search(rf'^{name}\s*=\s*(.+?)\s*$', content, re.MULTILINE)
    return match.group(1).strip() if match else None


def collect_content_names(content_path: Path, namespace: str) -> set[str]:
    if not content_path.is_file():
        return set()
    content = read_text(content_path)
    match = re.search(rf'^namespace {namespace}\s*$(.*?)(?=^namespace \w|\Z)', content, re.MULTILINE | re.DOTALL)
    scope = match.group(1) if match else content
    return set(CONTENT_CONST_RE.findall(scope))


def collect_items(items_dir: Path) -> dict[str, list[str]]:
    categories: dict[str, list[str]] = {name: [] for name in CATEGORY_ORDER}

    for path in sorted(items_dir.glob('*.foitem')):
        content = read_text(path)
        proto_type = parse_field(content, 'Type')
        if proto_type is None or proto_type not in CATEGORY_BY_TYPE:
            continue

        name = parse_field(content, r'\$Name') or path.stem
        if name:
            categories[CATEGORY_BY_TYPE[proto_type]].append(name)

    return categories


def collect_locations(maps_dir: Path) -> dict[str, list[str]]:
    locations: dict[str, list[str]] = {}

    for path in sorted(maps_dir.glob('*.foloc')):
        content = read_text(path)
        raw = parse_field(content, 'MapProtos')
        locations[path.stem] = raw.split() if raw else []

    return locations


def identifier(name: str, content_names: set[str], namespace: str) -> str:
    if name in content_names:
        return f'Content::{namespace}::{name}'
    return f'"{name}".hstr()'


def generate(categories: dict[str, list[str]], item_names: set[str], loc_names: set[str], map_names: set[str], line_ending: str) -> str:
    lines: list[str] = []
    lines.append('// DebugCatalog — сгенерированный по прототипам каталог предметов, локаций и субкарт для дебаг-меню.')
    lines.append('// Источник: Items/*.foitem, Maps/*.foloc + Scripts/Content.fos (namespace Item/Location/Map).')
    lines.append('// Генерируется Tools/generate_debug_catalog.py. Не редактировать вручную.')
    lines.append('namespace DebugCatalog')
    lines.append('{')
    lines.append('')
    lines.append('#if CLIENT')
    lines.append('')

    for category in CATEGORY_ORDER:
        names = categories[category]
        content_names = loc_names if category == 'Locations' else item_names
        namespace = 'Location' if category == 'Locations' else 'Item'
        lines.append(f'hstring[] {category} = {{')
        for name in names:
            lines.append(f'    {identifier(name, content_names, namespace)},')
        lines.append('};')
        lines.append('')

    # Субкарты по локациям (порядок как в .foloc MapProtos).
    for loc_name, maps in locations_map.items():
        lines.append(f'hstring[] LocMaps_{loc_name} = {{')
        for map_pid in maps:
            lines.append(f'    {identifier(map_pid, map_names, "Map")},')
        lines.append('};')
        lines.append('')

    lines.append('hstring[] GetLocationMaps(hstring locPid)')
    lines.append('{')
    for loc_name in locations_map:
        lines.append(f'    if (locPid == {identifier(loc_name, loc_names, "Location")}) {{')
        lines.append(f'        return LocMaps_{loc_name};')
        lines.append('    }')
    lines.append('')
    lines.append('    return array<hstring>();')
    lines.append('}')

    lines.append('')
    lines.append('#endif')
    lines.append('')
    lines.append('}')

    return line_ending.join(lines) + line_ending


locations_map: dict[str, list[str]] = {}


def main() -> int:
    global locations_map

    parser = argparse.ArgumentParser(description='Generate Scripts/DebugCatalog.fos from Items/Maps prototypes')
    parser.add_argument('--project-root', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()

    project_root = args.project_root.resolve() if args.project_root else Path(__file__).resolve().parents[1]
    content_path = project_root / 'Scripts' / 'Content.fos'
    output_path = args.output.resolve() if args.output else project_root / 'Scripts' / 'DebugCatalog.fos'

    line_ending = '\r\n'
    if output_path.is_file() and '\r\n' not in read_text(output_path):
        line_ending = '\n'

    item_names = collect_content_names(content_path, 'Item')
    loc_names = collect_content_names(content_path, 'Location')
    map_names = collect_content_names(content_path, 'Map')

    categories = collect_items(project_root / 'Items')
    locations_map = collect_locations(project_root / 'Maps')
    categories['Locations'] = list(locations_map.keys())
    for names in categories.values():
        names.sort(key=str.lower)

    total_items = sum(len(categories[name]) for name in CATEGORY_ORDER if name != 'Locations')
    output = generate(categories, item_names, loc_names, map_names, line_ending)
    output_path.write_bytes(output.encode('utf-8'))

    counts = ', '.join(f'{name}={len(categories[name])}' for name in CATEGORY_ORDER)
    print(f'[DebugCatalog] items={total_items} ({counts}) -> {output_path.name}', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
