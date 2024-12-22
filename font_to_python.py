import freetype
import os

def fon_to_python(fon_path):
    """Convert a bitmap font to Python"""
    # Load the font
    face = freetype.Face(fon_path)
    
    # Get dimensions from filename (e.g. Bm437_EverexME_5x8.FON)
    base = os.path.basename(fon_path)
    if 'x' in base:
        width = int(base.split('x')[0][-1])
        height = int(base.split('x')[1].split('.')[0])
    else:
        # Try to get from font metrics
        width = face.max_advance_width
        height = face.height
    
    # Set pixel size
    face.set_pixel_sizes(width, height)
    
    char_map = {}
    
    # Process each printable ASCII character
    for char in range(32, 127):
        try:
            # Load character - add 1 to fix offset
            face.load_char(chr(char + 1), freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_MONO)
            
            # Get bitmap
            bitmap = face.glyph.bitmap
            
            # Convert to pixel array
            pixels = []
            for y in range(height):
                row = []
                for x in range(width):
                    if y < bitmap.rows and x < bitmap.width:
                        # Get pixel from bitmap
                        byte_index = y * bitmap.pitch + (x >> 3)
                        if byte_index < len(bitmap.buffer):
                            pixel = (bitmap.buffer[byte_index] & (1 << (7 - (x & 7)))) != 0
                            row.append(1 if pixel else 0)
                        else:
                            row.append(0)
                    else:
                        row.append(0)
                pixels.append(row)
            
            char_map[chr(char)] = pixels
            
        except Exception as e:
            print(f"Error processing character {chr(char)}: {e}")
            # Use empty bitmap for failed characters
            char_map[chr(char)] = [[0] * width for _ in range(height)]
    
    # Generate output filename based on dimensions
    output_path = f'font_{width}x{height}.py'
    
    # Write Python file
    with open(output_path, 'w') as f:
        f.write(f'# Auto-generated font file from {os.path.basename(fon_path)}\n')
        f.write(f'# Font size: {width}x{height} pixels\n\n')
        
        f.write(f'FONT_{width}X{height} = ' + '{\n')
        
        for char, bitmap in sorted(char_map.items()):
            f.write(f"    {repr(char)}: [\n")
            for row in bitmap:
                f.write(f"        {row},\n")
            f.write('    ],\n')
        
        f.write('}\n\n\n')
        
        f.write(f'def get_char(char: str) -> list:\n')
        f.write(f'    """Returns {width}x{height} bitmap for given character"""\n')
        f.write(f'    return FONT_{width}X{height}.get(char, FONT_{width}X{height}["?"])\n\n\n')
        
        f.write('def get_text_width(text: str) -> int:\n')
        f.write(f'    """Returns pixel width of text using {width}x{height} font"""\n')
        f.write(f'    return len(text) * {width}\n')
    
    print(f"Generated {output_path} with {width}x{height} pixel font")
    return output_path, width, height

if __name__ == '__main__':
    # Convert both fonts
    fon_files = [
        'font_5x8.FON',  # 5x8 font
        'font_8x16.FON'   # 8x16 font
    ]
    
    for fon_file in fon_files:
        try:
            output_path, width, height = fon_to_python(fon_file)
            print(f"Successfully converted {fon_file} to {output_path}")
        except Exception as e:
            print(f"Error converting {fon_file}: {e}")
