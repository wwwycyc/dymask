import json
from collections import Counter

with open('assets/PIE-Bench/mapping_file.json', 'r') as f:
    data = json.load(f)

keys = list(data.keys())
print('Total entries:', len(keys))
print('First key:', keys[0])
print()
entry = data[keys[0]]
for k, v in entry.items():
    if k == 'mask':
        print(f'  mask: type={type(v).__name__}, len={len(v) if hasattr(v, "__len__") else "N/A"}')
        if isinstance(v, dict):
            for mk, mv in v.items():
                print(f'    {mk}: {str(mv)[:100]}')
        else:
            print(f'  mask sample: {str(v)[:120]}')
    else:
        print(f'  {k}: {v}')

print()
types = Counter(v['editing_type_id'] for v in data.values())
print('editing_type_id distribution:', dict(sorted(types.items())))

# sample a few more entries
print()
for key in keys[1:4]:
    e = data[key]
    print(f'[{key}] type={e["editing_type_id"]} | blended_word={e.get("blended_word")} | image_path={e["image_path"]}')
