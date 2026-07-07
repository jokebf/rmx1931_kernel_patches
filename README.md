# RMX1931 Kernel Patches — Charging Fix

Patches for Realme X2 Pro (samurai) custom ROM kernel charging issues.

## Patches Included

| Patch | Fixes | Effect |
|-------|-------|--------|
| `0001-charger-fix-deadlock.patch` | State machine stuck after charge stop | Charge resumes after temp/soc condition clears |
| `0002-skip-chargerid-switch-during-vooc.patch` | usbtemp_kthread kills VOOC MCU | VOOC stable during USB temp monitoring |

## How to Build (GitHub Actions)

### Step 1: Push patches to your GitHub

```bash
# Clone this repo or create your own
git clone https://github.com/YOUR_USERNAME/rmx1931_kernel_patches
cd rmx1931_kernel_patches

# Push to GitHub
git remote add origin https://github.com/YOUR_USERNAME/rmx1931_kernel_patches
git push -u origin main
```

### Step 2: Run the Action

1. Go to your repo → Actions tab
2. Select "Build RMX1931 (samurai) Kernel"
3. Click "Run workflow" → choose branch `lineage-20`
4. Wait ~20-30 minutes for build to complete

### Step 3: Download & Flash

1. Download `rmx1931-kernel-lineage-20.zip` artifact
2. Extract `Image.gz-dtb`
3. Flash via TWRP or `dd`:

**Option A — TWRP:**
- Boot to TWRP
- Advanced → Install Recovery Ramdisk → select `boot.img` (if you repack)

**Option B — DD (fastboot):**
```bash
# First backup current boot
adb shell "dd if=/dev/block/by-name/boot of=/sdcard/boot_stock.img"

# On PC, repack boot.img with new kernel:
# (You need your ROM's stock boot.img and mkbootimg tool)

# Flash via fastboot
fastboot flash boot new_boot.img
```

## DIY: Build Locally

```bash
# Get kernel source
git clone --depth=1 -b lineage-20 \
  https://github.com/HyperTeam/android_kernel_realme_sm8150.git kernel
cd kernel

# Apply patches
git am /path/to/0001*.patch /path/to/0002*.patch

# Build
export ARCH=arm64
export CROSS_COMPILE=aarch64-linux-gnu-
make samurai_defconfig
make -j$(nproc)
# Output: out/arch/arm64/boot/Image.gz-dtb
```

## Credits

- Kernel source: [HyperTeam/android_kernel_realme_sm8150](https://github.com/HyperTeam/android_kernel_realme_sm8150)
- ROM: crDroid 9.9 by @karthick111
