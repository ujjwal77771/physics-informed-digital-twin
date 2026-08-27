import re

with open("README.md", "r", encoding="utf-8") as f:
    text = f.read()

# Completely remove the broken performance section and replace it cleanly
# We will use string splitting to isolate the section
parts = text.split("## Performance")
if len(parts) > 1:
    before = parts[0]
    after = parts[1]
    
    # Find the next section heading (starts with ## )
    next_section_idx = after.find("\n## Limitations")
    if next_section_idx != -1:
        after_performance = after[next_section_idx:]
    else:
        after_performance = ""

    new_performance = """## Performance

Evaluated using 3-Fold Cross-Validation on the NASA C-MAPSS Turbofan Engine Dataset (FD001, FD002, FD003):

| Model Configuration | RMSE (Cycles) | Standard Deviation |
|---------------------|---------------|--------------------|
| LSTM (Baseline) | 41.44 | +/- 0.23 |
| VibFormer (Data Only - No Physics) | 40.88 | +/- 41.37 |
| VibFormer (Physics Only) | 14.10 | +/- 0.65 |
| VibFormer (Monotonicity Only) | 11.54 | +/- 2.14 |
| **VibFormer (Full Physics + Mono)** | **11.31** | **+/- 0.36** |

**Key Insights:**
- Without physics constraints, the data-only Transformer is highly unstable (standard deviation of +/- 41.37).
- The hybrid physics + monotonicity loss stabilizes the Transformer (variance drops to +/- 0.36) and outperforms the LSTM baseline by 72.7%.
- Inference latency (ONNX, CPU): ~3.2 ms / window

---
"""
    
    text = before + new_performance + after_performance
    
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(text)
    print("Fixed README.md Performance Section!")
else:
    print("Could not find Performance section.")
