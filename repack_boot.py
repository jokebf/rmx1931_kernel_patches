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
    """Extract ramdisk and kernel from boot.img using unpackbootimg style"""
    os.makedirs(out_dir, exist_ok=True)
    
    with open(boot_img_path, 'rb') as f:
        data = f.read()
    
    # Android boot image header (v2/v3)
    # magic: 'ANDROID!' (8 bytes)
    magic = data[:8]
    if magic != b'ANDROID!':
        print(f"ERROR: Not a boot image (magic: {magic})")
        return False
    
    # Parse header
    kernel_size = struct.unpack_from('<I', data, 8)[0]
    kernel_addr = struct.unpack_from('<I', data, 12)[0]
    ramdisk_size = struct.unpack_from('<I', data, 16)[0]
    ramdisk_addr = struct.unpack_from('<I', data, 20)[0]
    second_size = struct.unpack_from('<I', data, 24)[0]
    second_addr = struct.unpack_from('<I', data, 28)[0]
    tags_addr = struct.unpack_from('<I', data, 32)[0]
    page_size = struct.unpack_from('<I', data, 36)[0]
    header_version = struct.unpack_from('<I', data, 40)[0]
    
    print(f"Boot image info:")
    print(f"  Page size: {page_size}")
    print(f"  Kernel size: {kernel_size}")
    print(f"  Ramdisk size: {ramdisk_size}")
    print(f"  Header version: {header_version}")
    
    # Calculate kernel offset (after header, page-aligned)
    header_size = (1 + header_version) * page_size
    if header_version >= 3:
        # For v3+, kernel starts at offset 4096
        kernel_offset = page_size
        kernel_data = data[kernel_offset:kernel_offset + kernel_size]
        ramdisk_offset = kernel_offset + ((kernel_size + page_size - 1) // page_size) * page_size
        ramdisk_data = data[ramdisk_offset:ramdisk_offset + ramdisk_size]
    else:
        # v0/v1/v2
        kernel_offset = page_size  # After header
        kernel_data = data[kernel_offset:kernel_offset + kernel_size]
        ramdisk_offset = kernel_offset + ((kernel_size + page_size - 1) // page_size) * page_size
        ramdisk_data = data[ramdisk_offset:ramdisk_offset + ramdisk_size]
    
    # Save extracted data
    with open(f"{out_dir}/kernel.orig", 'wb') as f:
        f.write(kernel_data)
    with open(f"{out_dir}/ramdisk.gz", 'wb') as f:
        f.write(ramdisk_data)
    with open(f"{out_dir}/header.bin", 'wb') as f:
        f.write(data[:page_size])
    
    print(f"  Saved: kernel.orig ({len(kernel_data)} bytes)")
    print(f"  Saved: ramdisk.gz ({len(ramdisk_data)} bytes)")
    print(f"  Saved: header.bin ({page_size} bytes)")
    
    return True

def repack_bootimg(out_dir, new_kernel_path, output_path):
    """Replace kernel and repack boot.img"""
    with open(f"{out_dir}/header.bin", 'rb') as f:
        header = bytearray(f.read())
    
    with open(f"{out_dir}/ramdisk.gz", 'rb') as f:
        ramdisk_data = f.read()
    
    with open(new_kernel_path, 'rb') as f:
        new_kernel = f.read()
    
    # Parse header to get addresses
    page_size = struct.unpack_from('<I', bytes(header), 36)[0]
    kernel_addr = struct.unpack_from('<I', bytes(header), 12)[0]
    ramdisk_addr = struct.unpack_from('<I', bytes(header), 20)[0]
    tags_addr = struct.unpack_from('<I', bytes(header), 32)[0]
    header_version = struct.unpack_from('<I', bytes(header), 40)[0]
    
    print(f"Repacking with new kernel ({len(new_kernel)} bytes)")
    print(f"  Ramdisk: {len(ramdisk_data)} bytes")
    print(f"  Page size: {page_size}")
    print(f"  Header version: {header_version}")
    
    # Update kernel size in header
    struct.pack_into('<I', header, 8, len(new_kernel))
    
    # Recalculate sizes
    header_size = (1 + header_version) * page_size
    kernel_pages = (len(new_kernel) + page_size - 1) // page_size
    ramdisk_pages = (len(ramdisk_data) + page_size - 1) // page_size
    
    # Recalculate total size and write
    total_size = header_size + kernel_pages * page_size + ramdisk_pages * page_size
    
    with open(output_path, 'wb') as f:
        # Write header
        f.write(bytes(header))
        # Pad to kernel offset
        current = header_size
        if current < header_size:
            f.write(b'\x00' * (header_size - current))
        
        # Write kernel
        f.write(new_kernel)
        # Pad to page boundary
        kernel_used = len(new_kernel)
        kernel_padded = kernel_pages * page_size
        if kernel_used < kernel_padded:
            f.write(b'\x00' * (kernel_padded - kernel_used))
        
        # Write ramdisk
        f.write(ramdisk_data)
        ramdisk_used = len(ramdisk_data)
        ramdisk_padded = ramdisk_pages * page_size
        if ramdisk_used < ramdisk_padded:
            f.write(b'\x00' * (ramdisk_padded - ramdisk_used))
    
    actual_size = os.path.getsize(output_path)
    print(f"  Created: {output_path} ({actual_size} bytes)")
    print(f"  Match stock size: {'OK' if actual_size <= os.path.getsize(f'{out_dir}/header.bin') + os.path.getsize(f'{out_dir}/kernel.orig') + os.path.getsize(f'{out_dir}/ramdisk.gz') + page_size * 2 else 'WARNING: larger'}")
    
    return True

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage:")
        print("  Unpack: repack_boot.py unpack <boot.img> <out_dir>")
        print("  Repack: repack_boot.py repack <out_dir> <new_kernel> <output_boot.img>")
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
