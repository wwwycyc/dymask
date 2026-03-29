import pyarrow.parquet as pq
from collections import Counter

f = pq.ParquetFile('assets/data/V1-00000-of-00001.parquet')
t = f.read()
rows = t.to_pydict()
masks = rows['mask']

zero_count = sum(1 for m in masks if m == '0 262144' or m == '0 262143')
nonempty = [m for m in masks if m and m not in ('0 262144', '0 262143')]
print(f'Total rows: {len(masks)}')
print(f'All-zero masks: {zero_count}')
print(f'Non-zero masks: {len(nonempty)}')
if nonempty:
    print('Sample non-zero masks:')
    for m in nonempty[:5]:
        print(' ', str(m)[:120])
