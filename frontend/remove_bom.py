import re
path = r'C:\Users\Richi\Desktop\Caremate AI\frontend\src\app\dashboard\page.tsx'
with open(path, 'r', encoding='utf-8-sig') as f:
    content = f.read()
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("BOM removed")
