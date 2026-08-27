import re

with open("README.md", "r", encoding="utf-8") as f:
    text = f.read()

# Fix the year
text = text.replace("3rd year", "3rd year")
text = text.replace("3rd year", "3rd Year")
text = text.replace("third year", "Third year")

# Replace the Performance section
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

---"""

# Find the section and replace it
text = re.sub(r'## Performance\n\n.*?---', new_performance, text, flags=re.DOTALL)

with open("README.md", "w", encoding="utf-8") as f:
    f.write(text)
print("Updated README.md")
