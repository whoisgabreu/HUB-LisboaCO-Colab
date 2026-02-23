import os
import re

def fix_styles_css(filepath):
    if not os.path.exists(filepath):
        print(f"File {filepath} not found.")
        return

    # Read with latin-1 to avoid decode errors
    with open(filepath, 'r', encoding='latin-1') as f:
        lines = f.readlines()

    new_lines = []
    
    # Define variables at the top
    vars_block = [
        ":root {\n",
        "    --header-height: 82px;\n",
        "    --bg-main: #000000;\n",
        "    --bg-hover: #17171b;\n",
        "    --card-bg: #1e1e24;\n",
        "    --modal-bg: #1c1c21;\n",
        "    --text-main: #ffffff;\n",
        "    --text-muted: #a0a0a0;\n",
        "    --border-color: rgba(255, 255, 255, 0.1);\n",
        "    --accent-red: #d61616;\n",
        "}\n\n"
    ]
    
    # Skip existing :root if present
    in_root = False
    started = False
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(':root {'):
            in_root = True
            if not started:
                new_lines.extend(vars_block)
                started = True
            continue
        if in_root and '}' in line:
            in_root = False
            continue
        if in_root:
            continue
            
        if not started:
            new_lines.extend(vars_block)
            started = True

        # Expand line 2506 mess if detected
        if '/* OPERACAO REFINED STYLES */' in line:
            # Simple expansion by adding newlines after semicolons and braces
            expanded = line.replace('}', '}\n').replace(';', ';\n').replace('{', ' {\n')
            for exp_line in expanded.split('\n'):
                if exp_line.strip():
                    new_lines.append(exp_line + '\n')
            continue

        # Fix the broken content property
        line = line.replace('content: " \\;', 'content: "";')
        
        # Replace colors with variables
        # Using regex to match hex colors strictly
        line = line.replace('#000000', 'var(--bg-main)')
        line = line.replace('#17171b', 'var(--bg-hover)')
        line = line.replace('#1e1e24', 'var(--card-bg)')
        line = line.replace('#1c1c21', 'var(--modal-bg)')
        line = line.replace('#ffffff', 'var(--text-main)')
        # Note: we should be careful with #fff as it might be used in images or specific props
        # But for text color: #fff; it's safe.
        line = re.sub(r'color:\s*#fff(\s*|;)', r'color: var(--text-main)\1', line)
        line = re.sub(r'color:\s*#ffffff(\s*|;)', r'color: var(--text-main)\1', line)
        line = line.replace('background: #17171b', 'background: var(--bg-hover)')
        line = line.replace('background-color: #17171b', 'background-color: var(--bg-hover)')
        
        new_lines.append(line)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print("Fixed styles.css successfully.")

if __name__ == "__main__":
    fix_styles_css(r'C:\Users\Gabriel\Documents\Projetos\HUB-LisboaCO-Colab\static\style\styles.css')
