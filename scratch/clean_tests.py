
import re

with open('tests/test_automations.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace box drawing
content = content.replace('━', '-').replace('═', '=').replace('║', '|')
# Replace emojis
content = content.replace('✅', '[PASS]').replace('❌', '[FAIL]').replace('💥', '[ERROR]').replace('←', '<-')

with open('tests/test_automations.py', 'w', encoding='utf-8') as f:
    f.write(content)
