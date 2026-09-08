import sys
from io import StringIO
from demo_v0 import main

buf = StringIO()
old_stdout = sys.stdout
sys.stdout = buf
try:
    main()
finally:
    sys.stdout = old_stdout

output = buf.getvalue()
print(output)

with open("E:/must-assesment/demo_output.txt", "w", encoding="utf-8") as f:
    f.write(output)

print("\n[output saved to demo_output.txt]")
