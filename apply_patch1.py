#!/usr/bin/env python3
"""Apply patch 1: Fix charger deadlock state machine"""
import sys, os

def main():
    path = sys.argv[1]
    with open(path) as f: content = f.read()
    
    print(f"Patching: {path}")
    
    # 1. /*do nothing*/ → charger_resumed = false;
    if '/*do nothing*/' in content:
        content = content.replace('/*do nothing*/', 'charger_resumed = false;')
        print("  ✓ Added charger_resumed reset")
    
    # 2. Remove && charger_resumed == false from condition
    old2 = ('\t\t\t} else if (oplus_vooc_get_fastchg_started() == false\n'
            '\t\t\t\t\t&& charger_resumed == false) {')
    new2 = '\t\t\t} else if (oplus_vooc_get_fastchg_started() == false) {'
    if old2 in content:
        content = content.replace(old2, new2)
        print("  ✓ Removed charger_resumed condition")
    else:
        # Try single-line form
        old2b = '\t\t\t} else if (oplus_vooc_get_fastchg_started() == false && charger_resumed == false) {'
        if old2b in content:
            content = content.replace(old2b, new2)
            print("  ✓ Removed charger_resumed (single line)")
    
    # 3. Wrap check_charger_resume in if(!charger_resumed)
    old3 = ('\t\t\t\tcharger_resumed = chip->chg_ops->check_charger_resume();\n'
            '\t\t\t\toPlus_chg_turn_on_charging(chip);')
    new3 = ('\t\t\t\tif (!charger_resumed)\n'
            '\t\t\t\t\tcharger_resumed = chip->chg_ops->check_charger_resume();\n'
            '\t\t\t\toPlus_chg_turn_on_charging(chip);')
    
    for prefix in ['oplus_chg', 'oPlus_chg', 'OPLUS_CHG']:
        check = old3.replace('oPlus_chg', prefix)
        repl = new3.replace('oPlus_chg', prefix)
        if check in content:
            content = content.replace(check, repl)
            print(f"  ✓ Wrapped check_charger_resume for {prefix}")
            break
    else:
        print("  ⚠ check_charger_resume pattern not found, searching...")
        import re
        for m in re.finditer(r'charger_resumed = chip->chg_ops->check_charger_resume\(\);.*?\n.*?turn_on_charging', content, re.DOTALL):
            print(f"  Found at pos {m.start()}: {m.group()[:80]}")

    # Save
    with open(path, 'w') as f:
        f.write(content)
    print("  ✓ Saved")

if __name__ == '__main__':
    main()
