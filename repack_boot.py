#!/usr/bin/env python3
"""
RMX1931 boot.img repacker
Replaces kernel in stock boot.img with custom-built Image.gz-dtb
"""
import struct
import sys
import os
import hashlib

def unpack_bootimg(boot_img_path, out_dir):
    """Extract ramdisk and kernel from boot.img"""
    os.makedirs(out_dir, exist_ok=True)
    
    with open(boot_img_path, 'rb') as f:
        data = f.read()
    
    # Android boot image magic
    magic = data[:8]
    if magic != b'ANDROID!':
        print(f"ERROR: Not a boot image (magic: {magic})")
        return False
    
    # Parse header
    kernel_size = struct.unpack_from('<I', data, 8)[0]
    ramdisk_size = struct.unpack_from('<I', data, 16)[0]
    page_size = struct.unpack_from('<I', data, 36)[0]
    header_version = struct.unpack_from('<I', data, 40)[0]
    
    print(f"Boot image info:")
    print(f"  Page size: {page_size}")
    print(f"  Kernel size: {kernel_size}")
    print(f"  Ramdisk size: {ramdisk_size}")
    print(f"  Header version: {header_version}")
    
    # Header occupies (1 + header_version) pages
    header_size = (1 + header_version) * page_size
    kernel_offset = header_size
    kernel_data = data[kernel_offset:kernel_offset + kernel_size]
    
    # Ramdisk starts at the next page after kernel
    kernel_pages = (kernel_size + page_size - 1) // page_size
    ramdisk_offset = kernel_offset + kernel_pages * page_size
    ramdisk_data = data[ramdisk_offset:ramdisk_offset + ramdisk_size]
    
    # Save extracted data
    with open(f"{out_dir}/kernel.orig", 'wb') as f:
        f.write(kernel_data)
    with open(f"{out_dir}/ramdisk.gz", 'wb') as f:
        f.write(ramdisk_data)
    with open(f"{out_dir}/header.bin", 'wb') as f:
        f.write(data[:header_size])
    with open(f"{out_dir}/original_size.txt", 'w') as f:
        f.write(str(os.path.getsize(boot_img_path)))
    
    print(f"  Saved: kernel.orig ({len(kernel_data)} bytes)")
    print(f"  Saved: ramdisk.gz ({len(ramdisk_data)} bytes)")
    print(f"  Saved: header.bin ({header_size} bytes)")
    print(f"  Saved: original_size.txt ({os.path.getsize(boot_img_path)} bytes)")
    
    return True

def repack_bootimg(out_dir, new_kernel_path, output_path):
    """Replace kernel and repack boot.img"""
    with open(f"{out_dir}/header.bin", 'rb') as f:
        header = bytearray(f.read())
    
    with open(f"{out_dir}/ramdisk.gz", 'rb') as f:
        ramdisk_data = f.read()
    
    with open(new_kernel_path, 'rb') as f:
        new_kernel = f.read()
    
    # Get original boot.img size (for padding)
    original_size_file = f"{out_dir}/original_size.txt"
    original_size = 0
    if os.path.exists(original_size_file):
        with open(original_size_file) as f:
            original_size = int(f.read().strip())
    
    # Parse header
    page_size = struct.unpack_from('<I', bytes(header), 36)[0]
    header_version = struct.unpack_from('<I', bytes(header), 40)[0]
    
    print(f"Repacking with new kernel ({len(new_kernel)} bytes)")
    print(f"  Original kernel: {os.path.getsize(f'{out_dir}/kernel.orig')} bytes")
    print(f"  New kernel: {len(new_kernel)} bytes")
    print(f"  Ramdisk: {len(ramdisk_data)} bytes")
    print(f"  Page size: {page_size}")
    print(f"  Header version: {header_version}")
    print(f"  Original boot.img: {original_size} bytes")
    
    # Update kernel size in header
    struct.pack_into('<I', header, 8, len(new_kernel))
    
    # Recalculate sizes (page-aligned)
    header_size = (1 + header_version) * page_size
    kernel_pages = (len(new_kernel) + page_size - 1) // page_size
    ramdisk_pages = (len(ramdisk_data) + page_size - 1) // page_size
    
    payload_size = header_size + kernel_pages * page_size + ramdisk_pages * page_size
    
    with open(output_path, 'wb') as f:
        # Write full header (padded to header_size)
        f.write(bytes(header))
        current = len(header)
        if current < header_size:
            f.write(b'\x00' * (header_size - current))
        
        # Write kernel + padding
        f.write(new_kernel)
        kernel_pad = kernel_pages * page_size - len(new_kernel)
        if kernel_pad > 0:
            f.write(b'\x00' * kernel_pad)
        
        # Write ramdisk + padding
        f.write(ramdisk_data)
        ramdisk_pad = ramdisk_pages * page_size - len(ramdisk_data)
        if ramdisk_pad > 0:
            f.write(b'\x00' * ramdisk_pad)
        
        # Pad to original boot.img size (if known)
        if original_size > payload_size:
            f.write(b'\x00' * (original_size - payload_size))
    
    actual_size = os.path.getsize(output_path)
    print(f"  Created: {output_path} ({actual_size} bytes)")
    if original_size:
        print(f"  Matches original size: {'YES ✓' if actual_size == original_size else 'NO ✗'}")
    
    return True

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage:")
        print("  Unpack: repack_boot.py unpack <boot.img> [out_dir]")
        print("  Repack: repack_boot.py repack <out_dir> <new_kernel> [output_boot.img]")
        sys.exit(1)
    
    action = sys.argv[1]
    
    if action == 'unpack':
        boot_img = sys.argv[2]
        out_dir = sys.argv[3] if len(sys.argv) > 3 else 'boot_out'
        unpack_bootimg(boot_img, out_dir)
    elif action == 'repack':
        out_dir = sys.argv[2]
        new_kernel = sys.argv[3]
        output = sys.argv[4] if len(sys.argv) > 4 else 'boot_patched.img'
        repack_bootimg(out_dir, new_kernel, output)
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)
