import os

def fix_css(filepath):
    if not os.path.exists(filepath):
        print(f"File {filepath} not found.")
        return

    # Try different encodings
    for encoding in ['utf-8', 'latin-1', 'cp1252']:
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                content = f.read()
            print(f"Read successful with {encoding}")
            break
        except UnicodeDecodeError:
            continue
    else:
        print("Could not read file with any encoding.")
        return

    # Replacements
    replacements = {
        'background-color: #000000;': 'background-color: var(--bg-main);',
        'background: #17171b;': 'background: var(--bg-hover);',
        'background-color: #17171b;': 'background-color: var(--bg-hover);',
        'background: #1e1e24;': 'background: var(--card-bg);',
        'color: #fff;': 'color: var(--text-main);',
        'color: #ffffff;': 'color: var(--text-main);',
        'background: #1c1c21;': 'background: var(--modal-bg);',
        'background-color: #1c1c21;': 'background-color: var(--modal-bg);',
        'border: 1px solid rgba(255, 0, 0, 0.2);': 'border: 1px solid var(--border-color);',
        'border-bottom: 1px solid rgba(255, 0, 0, 0.2);': 'border-bottom: 1px solid var(--border-color);'
    }

    for search, replace in replacements.items():
        content = content.replace(search, replace)
    
    # Specific modal fix
    if '.gt-modal-content {' in content:
        content = content.replace('.gt-modal-content {', '.gt-modal-content {\n      background: var(--modal-bg);')
    if '.gt-modal-title {' in content:
        content = content.replace('.gt-modal-title {', '.gt-modal-title {\n      color: var(--text-main);')

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Fixed {filepath}")

if __name__ == "__main__":
    fix_css(r'C:\Users\Gabriel\Documents\Projetos\HUB-LisboaCO-Colab\static\style\styles.css')
