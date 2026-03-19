# -*- coding: utf-8 -*-
import os
import chardet  # type: ignore[import-not-found]

# 需要转换的文件
files_to_convert = []
for root, dirs, files in os.walk('src'):
    for file in files:
        if file.endswith(('.tsx', '.ts', '.css')):
            files_to_convert.append(os.path.join(root, file))

print(f'Found {len(files_to_convert)} files to check')

converted = 0
for filepath in files_to_convert[:30]:  # 限制处理 30 个文件
    try:
        with open(filepath, 'rb') as f:
            content = f.read()
        
        # 检测编码
        result = chardet.detect(content)
        if result['encoding'] and 'GB' in result['encoding'].upper():
            # GBK 编码，需要转换
            text = content.decode('gbk', errors='replace')
            with open(filepath, 'w', encoding='utf-8-sig') as f:
                f.write(text)
            print(f'✓ Converted: {filepath}')
            converted += 1
        else:
            print(f'- Skip (UTF-8): {filepath}')
    except Exception as e:
        print(f'✗ Error: {filepath} - {e}')

print(f'\nTotal converted: {converted} files')
