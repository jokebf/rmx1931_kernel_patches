#!/usr/bin/env python3
"""
Apply charging fix patches to oplus_charger.c
Usage: python3 apply_charger_fix.py <path-to-oplus_charger.c>
"""
import sys
import re
import os

def apply_patch1(content):
    """Fix charger deadlock - state machine resume"""
    # Replace 1: /*do nothing*/ → charger_resumed = false;
    content = content.replace(
        '/*do nothing*/',
        'charger_resumed = false;'
    )
    
    # Replace 2: Remove charger_resumed == false from else-if condition
    # Old: } else if (oplus_vooc_get_fastchg_started() == false\n\t\t\t\t\t&& charger_resumed == false) {
    # New: } else if (oplus_vooc_get_fastchg_started() == false) {
    old = (
        '\t\t\t} else if (oplus_vooc_get_fastchg_started() == false\n'
        '\t\t\t\t\t&& charger_resumed == false) {'
    )
    new = '\t\t\t} else if (oplus_vooc_get_fastchg_started() == false) {'
    if old in content:
        content = content.replace(old, new)
        print("  ✓ Patch 1a: Removed charger_resumed condition")
    else:
        print("  ⚠ Patch 1a: Pattern not found - trying alternate...")
        # Try alternate format
        alt_old = '} else if (oplus_vooc_get_fastchg_started() == false\n\t\t\t\t\t&& charger_resumed == false) {'
        alt_new = '} else if (oplus_vooc_get_fastchg_started() == false) {'
        if alt_old in content:
            content = content.replace(alt_old, alt_new)
            print("  ✓ Patch 1a: Applied via alt pattern")
        else:
            print("  ✗ Patch 1a: FAILED")
    
    # Replace 3: Wrap check_charger_resume in if(!charger_resumed)
    old = (
        '\t\t\t\tcharger_resumed = chip->chg_ops->check_charger_resume();\n'
        '\t\t\t\toPlus_chg_turn_on_charging(chip);'
    )
    new = (
        '\t\t\t\tif (!charger_resumed)\n'
        '\t\t\t\t\tcharger_resumed = chip->chg_ops->check_charger_resume();\n'
        '\t\t\t\toPlus_chg_turn_on_charging(chip);'
    )
    if old in content:
        # Check if it's oplus or oPlus or oplus
        for prefix in ['oplus', 'oPlus', 'OPLUS']:
            check_old = old.replace('oPlus', prefix)
            check_new = new.replace('oPlus', prefix)
            if check_old in content:
                content = content.replace(check_old, check_new)
                print(f"  ✓ Patch 1b: Wrapped check_charger_resume in if(!charger_resumed)")
                break
        else:
            print("  ✗ Patch 1b: Pattern not found")
    else:
        print("  ⚠ Patch 1b: Pattern not found in expected form")
    
    return content

def apply_patch2(content):
    """Skip chargerid switch during VOOC"""
    # Find the get_chargerid_voltage function
    marker = 'get charger id from mcu, chip->chargerid_volt = %d'
    
    # Find the block after the MCU path
    # Pattern: the } else { and everything inside
    old_pattern = (
        '\t\t\tchip->chargerid_volt);\n'
        '\t} else {\n'
        '\t\tif (chip->chg_ops->get_chargerid_switch_val() == 0) {\n'
        '\t\t\tchip->chg_ops->set_chargerid_switch_val(1);\n'
        '\t\t\toPlus_vooc_set_vooc_chargerid_switch_val(1);\n'
        '\t\t\tmsleep(100);\n'
        '\t\t\tchip->chargerid_volt = oPlus_chg_chargerid_voltage_check(chip);\n'
        '\t\t}\n'
        '\t}\n'
        '\n'
        '\tcharger_xlog_printk(CHG_LOG_CRTI,'
    )
    
    # Try different case variants
    for prefix in ['oplus', 'oPlus', 'OPLUS']:
        check_old = old_pattern.replace('oPlus', prefix)
        if check_old in content:
            new_block = (
                f'\t\t\tchip->chargerid_volt);\n'
                f'\t}}\n'
                f'\n'
                f'\t/* Don\'t touch chargerid switch if VOOC fast charging is active */\n'
                f'\tif ({prefix}_vooc_get_fastchg_started() == true) {{\n'
                f'\t\tcharger_xlog_printk(CHG_LOG_CRTI,\n'
                f'\t\t\t"fastchg active, skip chargerid switch\\n");\n'
                f'\t}} else if (chip->charger_exist) {{\n'
                f'\t\tif (chip->chg_ops->get_chargerid_switch_val() == 0) {{\n'
                f'\t\t\tchip->chg_ops->set_chargerid_switch_val(1);\n'
                f'\t\t\t{prefix}_vooc_set_vooc_chargerid_switch_val(1);\n'
                f'\t\t\tmsleep(100);\n'
                f'\t\t\tchip->chargerid_volt = {prefix}_chg_chargerid_voltage_check(chip);\n'
                f'\t\t}}\n'
                f'\t}}\n'
                f'\n'
                f'\tcharger_xlog_printk(CHG_LOG_CRTI,'
            )
            content = content.replace(check_old, new_block)
            print(f"  ✓ Patch 2: Added VOOC guard around chargerid switch")
            return content
    
    print("  ✗ Patch 2: Pattern not found - raw search...")
    # Fallback: search for the functions
    if marker in content:
        print("  Found marker, trying line-based approach")
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if marker in line and i + 5 < len(lines):
                # Found the area - check what comes next
                snippet = '\n'.join(lines[i:i+15])
                print(f"  Context around marker:\n{snippet}")
                break
    return content

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 apply_charger_fix.py <file>")
        sys.exit(1)
    
    path = sys.argv[1]
    if not os.path.exists(path):
        print(f"File not found: {path}")
        sys.exit(1)
    
    with open(path, 'r') as f:
        content = f.read()
    
    print(f"Applying patches to {path}")
    print(f"File size: {len(content)} bytes, {content.count(chr(10)) + 1} lines")
    
    content = apply_patch1(content)
    content = apply_patch2(content)
    
    # Write backup
    backup = path + '.bak'
    with open(backup, 'w') as f:
        f.write(open(path).read())
    print(f"Backup saved: {backup}")
    
    with open(path, 'w') as f:
        f.write(content)
    
    print(f"\nDone! Patched file written to {path}")
