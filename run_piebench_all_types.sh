#!/bin/bash
# Run PIE-Bench for all 10 editing types (0-9), 8 samples each
set -e

PIEBENCH_PATH="assets/PIE-Bench"
METHODS="target_only global_blend discrepancy_only discrepancy_attention discrepancy_latent full_dynamic_mask"
STEPS=20

for TYPE_ID in 0 1 2 3 4 5 6 7 8 9; do
    echo "===== Running type $TYPE_ID ====="
    conda run -n imgedit python DyMask/run_v1.py \
        --phase custom \
        --methods $METHODS \
        --piebench-path $PIEBENCH_PATH \
        --piebench-type-id $TYPE_ID \
        --sample-count 8 \
        --run-limit 8 \
        --num-inversion-steps $STEPS \
        --num-edit-steps $STEPS \
        --allow-download \
        --output-root runs/piebench_by_type
done

echo "All types done."
