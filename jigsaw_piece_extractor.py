#!/usr/bin/env python3

import argparse
import os
import numpy as np
from PIL import Image, ImageDraw

# Disable DecompressionBombWarning for large images
Image.MAX_IMAGE_PIXELS = None

import tempfile
import sys
import re
from cairosvg import svg2png
import xml.etree.ElementTree as ET
import shutil

def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Extract jigsaw puzzle pieces from an image using an SVG outline template'
    )
    parser.add_argument('image', type=str, help='Input image to be cut into puzzle pieces')
    parser.add_argument('svg', type=str, help='SVG file defining the jigsaw cuts')
    parser.add_argument('-o', '--output', type=str, default='pieces',
                        help='Output folder for the puzzle pieces (default: pieces)')
    parser.add_argument('--prefix', type=str, default='piece',
                        help='Prefix for output filenames (default: piece)')
    parser.add_argument('--format', type=str, default='png',
                        help='Output image format (default: png)')
    parser.add_argument('--padding', type=int, default=30,
                        help='Padding around pieces in pixels (default: 30)')
    parser.add_argument('--fixed-size', action='store_true',
                        help='Output all pieces with the same dimensions')
    parser.add_argument('--output-width', type=int, default=None,
                        help='Fixed width for output pieces (default: auto-calculated)')
    parser.add_argument('--output-height', type=int, default=None,
                        help='Fixed height for output pieces (default: auto-calculated)')
    parser.add_argument('--debug', action='store_true',
                        help='Save debug images')
    return parser.parse_args()

def get_svg_dimensions(svg_file):
    """Extract dimensions from SVG file"""
    tree = ET.parse(svg_file)
    root = tree.getroot()
    
    # Look for viewBox attribute
    if 'viewBox' in root.attrib:
        viewbox = root.attrib['viewBox'].split()
        width = float(viewbox[2])
        height = float(viewbox[3])
    else:
        # Look for width and height attributes
        width = height = None
        if 'width' in root.attrib:
            width_str = root.attrib['width']
            width = float(width_str.replace('mm', '').strip())
        if 'height' in root.attrib:
            height_str = root.attrib['height']
            height = float(height_str.replace('mm', '').strip())
        
        # Default values if nothing found
        if width is None: width = 300
        if height is None: height = 200
    
    return width, height

def determine_grid_size(svg_file):
    """Determine puzzle grid size from SVG file"""
    try:
        tree = ET.parse(svg_file)
        root = tree.getroot()
        
        # Get namespace
        ns = {'svg': 'http://www.w3.org/2000/svg'}
        
        # Find path elements
        paths = root.findall('.//svg:path', ns)
        
        if len(paths) < 3:
            # Try without namespace
            paths = root.findall('.//path')
        
        if len(paths) < 3:
            print("Warning: Could not find enough paths in SVG file, using default grid size.")
            return 4, 4
        
        # Get horizontal and vertical divider paths
        h_path = v_path = None
        
        # Look for darkblue/darkred paths if available
        for path in paths:
            stroke = path.get('stroke', '').lower()
            if stroke == 'darkblue' or (h_path is None and stroke == 'black'):
                h_path = path
            elif stroke == 'darkred' or (v_path is None and h_path is not None and stroke == 'black'):
                v_path = path
        
        # If we couldn't find colored paths, use the first two paths
        if h_path is None and len(paths) > 0:
            h_path = paths[0]
        if v_path is None and len(paths) > 1:
            v_path = paths[1]
        
        # Count M commands to determine rows and columns
        rows = cols = None
        
        if h_path is not None and 'd' in h_path.attrib:
            h_path_data = h_path.attrib['d']
            # Count M commands to determine number of horizontal dividers
            h_dividers = h_path_data.count('M ')
            rows = h_dividers + 1
        
        if v_path is not None and 'd' in v_path.attrib:
            v_path_data = v_path.attrib['d']
            # Count M commands to determine number of vertical dividers
            v_dividers = v_path_data.count('M ')
            cols = v_dividers + 1
        
        # Default values if we couldn't determine
        if rows is None: rows = 4
        if cols is None: cols = 4
        
        # Get SVG dimensions
        width, height = get_svg_dimensions(svg_file)
        
        return cols, rows, width, height
        
    except Exception as e:
        print(f"Error determining grid size: {e}")
        # Default values if there's an error
        return 4, 4, 300, 200

def create_horizontal_cut_svg(svg_file, temp_dir, row, rows, direction):
    """Create an SVG file that shows a single horizontal cut line
    direction: 'above' or 'below'
    """
    # Get SVG dimensions
    width, height = get_svg_dimensions(svg_file)
    
    # Parse the original SVG to get the paths
    with open(svg_file, 'r') as f:
        svg_content = f.read()
    
    # Extract path elements
    path_pattern = r'<path[^>]*d="([^"]*)"[^>]*>'
    paths = re.findall(path_pattern, svg_content)
    
    if len(paths) < 3:
        print("Not enough paths found in the SVG file")
        return None
    
    # Get the horizontal divider paths
    h_paths = paths[0]
    
    # Split the horizontal paths into segments
    h_segments = h_paths.split('M ')
    h_segments = [seg for seg in h_segments if seg.strip()]
    
    # Get the segment for this row
    if direction == 'above' and row > 0:
        segment_index = row - 1
    elif direction == 'below' and row < rows - 1:
        segment_index = row
    else:
        # This is an edge piece with no cut on this side
        return None
    
    if segment_index < len(h_segments):
        segment = h_segments[segment_index]
    else:
        print(f"Segment index {segment_index} out of range for horizontal segments")
        return None
    
    # Create a new SVG with just this cut line
    cut_svg = f'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect x="0" y="0" width="{width}" height="{height}" fill="white"/>
  <path d="M {segment}" stroke="black" stroke-width="1" fill="none"/>
</svg>'''
    
    # Write the SVG file
    cut_svg_path = os.path.join(temp_dir, f"h_cut_{row}_{direction}.svg")
    with open(cut_svg_path, 'w') as f:
        f.write(cut_svg)
    
    return cut_svg_path

def create_vertical_cut_svg(svg_file, temp_dir, col, cols, direction):
    """Create an SVG file that shows a single vertical cut line
    direction: 'left' or 'right'
    """
    # Get SVG dimensions
    width, height = get_svg_dimensions(svg_file)
    
    # Parse the original SVG to get the paths
    with open(svg_file, 'r') as f:
        svg_content = f.read()
    
    # Extract path elements
    path_pattern = r'<path[^>]*d="([^"]*)"[^>]*>'
    paths = re.findall(path_pattern, svg_content)
    
    if len(paths) < 3:
        print("Not enough paths found in the SVG file")
        return None
    
    # Get the vertical divider paths
    v_paths = paths[1]
    
    # Split the vertical paths into segments
    v_segments = v_paths.split('M ')
    v_segments = [seg for seg in v_segments if seg.strip()]
    
    # Get the segment for this column
    if direction == 'left' and col > 0:
        segment_index = col - 1
    elif direction == 'right' and col < cols - 1:
        segment_index = col
    else:
        # This is an edge piece with no cut on this side
        return None
    
    if segment_index < len(v_segments):
        segment = v_segments[segment_index]
    else:
        print(f"Segment index {segment_index} out of range for vertical segments")
        return None
    
    # Create a new SVG with just this cut line
    cut_svg = f'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect x="0" y="0" width="{width}" height="{height}" fill="white"/>
  <path d="M {segment}" stroke="black" stroke-width="1" fill="none"/>
</svg>'''
    
    # Write the SVG file
    cut_svg_path = os.path.join(temp_dir, f"v_cut_{col}_{direction}.svg")
    with open(cut_svg_path, 'w') as f:
        f.write(cut_svg)
    
    return cut_svg_path

def create_border_cut_svg(svg_file, temp_dir, row, col, rows, cols):
    """Create an SVG file that shows the border cut lines for edge pieces"""
    # Get SVG dimensions
    width, height = get_svg_dimensions(svg_file)
    
    # Parse the original SVG to get the paths
    with open(svg_file, 'r') as f:
        svg_content = f.read()
    
    # Extract path elements
    path_pattern = r'<path[^>]*d="([^"]*)"[^>]*>'
    paths = re.findall(path_pattern, svg_content)
    
    if len(paths) < 3:
        print("Not enough paths found in the SVG file")
        return None
    
    # Get the border path
    border = paths[2]
    
    # Create a new SVG with just the border
    cut_svg = f'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect x="0" y="0" width="{width}" height="{height}" fill="white"/>
  <path d="{border}" stroke="black" stroke-width="1" fill="none"/>
</svg>'''
    
    # Write the SVG file
    cut_svg_path = os.path.join(temp_dir, f"border_cut.svg")
    with open(cut_svg_path, 'w') as f:
        f.write(cut_svg)
    
    return cut_svg_path

def create_cut_masks(svg_file, temp_dir, row, col, rows, cols, img_width, img_height, debug=False):
    """Create mask images for the four cuts around a piece"""
    cut_masks = {}
    
    # Create horizontal cut above this piece
    h_above_svg = create_horizontal_cut_svg(svg_file, temp_dir, row, rows, 'above')
    if h_above_svg:
        h_above_png = os.path.join(temp_dir, f"h_above_{row}_{col}.png")
        svg2png(url=h_above_svg, write_to=h_above_png, 
              output_width=img_width, output_height=img_height)
        cut_masks['above'] = h_above_png
    
    # Create horizontal cut below this piece
    h_below_svg = create_horizontal_cut_svg(svg_file, temp_dir, row, rows, 'below')
    if h_below_svg:
        h_below_png = os.path.join(temp_dir, f"h_below_{row}_{col}.png")
        svg2png(url=h_below_svg, write_to=h_below_png, 
              output_width=img_width, output_height=img_height)
        cut_masks['below'] = h_below_png
    
    # Create vertical cut to the left of this piece
    v_left_svg = create_vertical_cut_svg(svg_file, temp_dir, col, cols, 'left')
    if v_left_svg:
        v_left_png = os.path.join(temp_dir, f"v_left_{row}_{col}.png")
        svg2png(url=v_left_svg, write_to=v_left_png, 
              output_width=img_width, output_height=img_height)
        cut_masks['left'] = v_left_png
    
    # Create vertical cut to the right of this piece
    v_right_svg = create_vertical_cut_svg(svg_file, temp_dir, col, cols, 'right')
    if v_right_svg:
        v_right_png = os.path.join(temp_dir, f"v_right_{row}_{col}.png")
        svg2png(url=v_right_svg, write_to=v_right_png, 
              output_width=img_width, output_height=img_height)
        cut_masks['right'] = v_right_png
    
    # Create border cut for edge pieces
    if row == 0 or row == rows - 1 or col == 0 or col == cols - 1:
        border_svg = create_border_cut_svg(svg_file, temp_dir, row, col, rows, cols)
        if border_svg:
            border_png = os.path.join(temp_dir, f"border_{row}_{col}.png")
            svg2png(url=border_svg, write_to=border_png, 
                  output_width=img_width, output_height=img_height)
            cut_masks['border'] = border_png
    
    return cut_masks

def center_and_resize_image(image, target_width, target_height):
    """Center an image in a new image of the specified dimensions"""
    # Create a new transparent image with the target dimensions
    new_image = Image.new('RGBA', (target_width, target_height), (0, 0, 0, 0))
    
    # Calculate the position to center the original image
    x_offset = (target_width - image.width) // 2
    y_offset = (target_height - image.height) // 2
    
    # Paste the original image onto the new image
    new_image.paste(image, (x_offset, y_offset))
    
    return new_image

def extract_puzzle_pieces(input_image, svg_file, output_folder, prefix="piece", format="png", 
                         padding=30, fixed_size=False, output_width=None, output_height=None, debug=False):
    """Extract puzzle pieces by applying four cuts to each piece position"""
    
    # Create output directory
    os.makedirs(output_folder, exist_ok=True)
    
    # Create temp directory
    temp_dir = tempfile.mkdtemp()
    debug_dir = os.path.join(output_folder, "debug") if debug else None
    
    if debug:
        os.makedirs(debug_dir, exist_ok=True)
    
    try:
        # Determine grid size
        cols, rows, svg_width, svg_height = determine_grid_size(svg_file)
        print(f"Detected puzzle grid: {cols} columns x {rows} rows")
        
        # Open input image
        input_img = Image.open(input_image)
        img_width, img_height = input_img.size
        
        # Convert input image to RGBA if it's not already
        if input_img.mode != 'RGBA':
            input_img = input_img.convert('RGBA')
        
        # Calculate cell dimensions in pixels
        cell_width = img_width / cols
        cell_height = img_height / rows
        
        # Create a master allocation map to track which pixels have already been assigned
        # This ensures no pixel is assigned to more than one piece
        allocation_map = np.zeros((img_height, img_width), dtype=np.uint8)
        
        # Variables to track the max piece dimensions for fixed_size output
        max_piece_width = 0
        max_piece_height = 0
        piece_bboxes = {}
        piece_images = {}
        
        # First pass: Create all piece masks without saving pieces
        piece_masks = {}
        for row in range(rows):
            for col in range(cols):
                print(f"Processing piece mask at position ({row}, {col})")
                
                # Create cut masks for this piece
                cut_masks = create_cut_masks(svg_file, temp_dir, row, col, rows, cols, 
                                           img_width, img_height, debug)
                
                # Create a mask for this piece that starts with all white (255)
                piece_mask = np.ones((img_height, img_width), dtype=np.uint8) * 255
                
                # Apply each cut mask
                for direction, mask_path in cut_masks.items():
                    # Load the cut mask
                    cut_mask = Image.open(mask_path).convert('L')
                    cut_array = np.array(cut_mask)
                    
                    # Threshold to ensure clean black/white
                    cut_array = (cut_array > 128).astype(np.uint8) * 255
                    
                    # Create a binary mask for the black pixels (the cut line)
                    cut_line = (cut_array == 0)
                    
                    # For each cut, we need to determine which side to keep
                    # and which side to discard
                    if direction == 'above':
                        # Keep pixels below the cut
                        discard_pixels = np.zeros_like(cut_line)
                        for x in range(img_width):
                            # Find the first black pixel (cut line) from top to bottom
                            cut_point = None
                            for y in range(img_height):
                                if cut_line[y, x]:
                                    cut_point = y
                                    break
                            
                            if cut_point is not None:
                                # Discard all pixels above the cut
                                discard_pixels[:cut_point, x] = True
                        
                        # Set discarded pixels to 0 in the piece mask
                        piece_mask[discard_pixels] = 0
                    
                    elif direction == 'below':
                        # Keep pixels above the cut
                        discard_pixels = np.zeros_like(cut_line)
                        for x in range(img_width):
                            # Find the first black pixel (cut line) from bottom to top
                            cut_points = []
                            for y in range(img_height - 1, -1, -1):
                                if cut_line[y, x]:
                                    cut_points.append(y)
                            
                            if cut_points:
                                # Use the topmost cut point
                                cut_point = min(cut_points)
                                # Discard all pixels below the cut
                                discard_pixels[cut_point:, x] = True
                        
                        # Set discarded pixels to 0 in the piece mask
                        piece_mask[discard_pixels] = 0
                    
                    elif direction == 'left':
                        # Keep pixels to the right of the cut
                        discard_pixels = np.zeros_like(cut_line)
                        for y in range(img_height):
                            # Find the first black pixel (cut line) from left to right
                            cut_point = None
                            for x in range(img_width):
                                if cut_line[y, x]:
                                    cut_point = x
                                    break
                            
                            if cut_point is not None:
                                # Discard all pixels to the left of the cut
                                discard_pixels[y, :cut_point] = True
                        
                        # Set discarded pixels to 0 in the piece mask
                        piece_mask[discard_pixels] = 0
                    
                    elif direction == 'right':
                        # Keep pixels to the left of the cut
                        discard_pixels = np.zeros_like(cut_line)
                        for y in range(img_height):
                            # Find the first black pixel (cut line) from right to left
                            cut_point = None
                            for x in range(img_width - 1, -1, -1):
                                if cut_line[y, x]:
                                    cut_point = x
                                    break
                            
                            if cut_point is not None:
                                # Discard all pixels to the right of the cut
                                discard_pixels[y, cut_point:] = True
                        
                        # Set discarded pixels to 0 in the piece mask
                        piece_mask[discard_pixels] = 0
                    
                    elif direction == 'border':
                        # For border pieces, handle each edge separately
                        if row == 0:  # Top edge
                            # Keep pixels below the border
                            for x in range(img_width):
                                # Find the first black pixel (border) from top to bottom
                                border_points = []
                                for y in range(img_height):
                                    if cut_line[y, x]:
                                        border_points.append(y)
                                
                                if border_points:
                                    # Use the bottommost point to avoid cutting too much
                                    border_point = max(border_points)
                                    # Discard all pixels above the border
                                    piece_mask[:border_point, x] = 0
                        
                        if row == rows - 1:  # Bottom edge
                            # For bottom edge, we need to keep a large part of the image below
                            # Just to ensure we're not accidentally removing the piece content,
                            # we'll only remove a few pixels at the very bottom of the image
                            piece_mask[-5:, :] = 0
                        
                        if col == 0:  # Left edge
                            # For left edge, just remove a few pixels at the very left of the image
                            # This ensures we don't accidentally remove the piece content
                            piece_mask[:, :5] = 0
                        
                        if col == cols - 1:  # Right edge
                            # For right edge, similarly ensure we're not removing the piece content
                            # Just remove a few pixels at the very right of the image
                            piece_mask[:, -5:] = 0
                
                # Store the mask for this piece
                piece_masks[(row, col)] = piece_mask
        
        # Second pass: Apply allocation rules to prevent overlapping pieces
        # Process pieces in a specific order (e.g., top-to-bottom, left-to-right)
        # to consistently assign boundary pixels
        for row in range(rows):
            for col in range(cols):
                current_mask = piece_masks[(row, col)]
                
                # For pixels that are claimed by this piece (mask value > 0)
                # only keep them if they haven't been allocated to another piece yet
                valid_pixels = (current_mask > 0) & (allocation_map == 0)
                
                # Create the final mask for this piece
                final_mask = np.zeros_like(current_mask)
                final_mask[valid_pixels] = 255
                
                # Update the allocation map to mark these pixels as allocated
                allocation_map[valid_pixels] = 1
                
                # Convert the numpy mask to PIL image
                final_mask_img = Image.fromarray(final_mask)
                
                # Save the mask for debugging
                if debug:
                    final_mask_img.save(os.path.join(debug_dir, f"piece_mask_{row}_{col}.png"))
                
                # Apply the mask to the input image
                piece_img = Image.new('RGBA', input_img.size, (0, 0, 0, 0))
                piece_img.paste(input_img, (0, 0), final_mask_img)
                
                # Find the bounding box of non-transparent pixels
                bbox = piece_img.getbbox()
                
                if bbox:
                    # Add padding
                    bbox = (
                        max(0, bbox[0] - padding),
                        max(0, bbox[1] - padding),
                        min(img_width, bbox[2] + padding),
                        min(img_height, bbox[3] + padding)
                    )
                    # Store the bounding box for later processing
                    piece_bboxes[(row, col)] = bbox
                    
                    # Crop the piece and store it
                    cropped_piece = piece_img.crop(bbox)
                    piece_images[(row, col)] = cropped_piece
                    
                    # Update maximum dimensions
                    max_piece_width = max(max_piece_width, cropped_piece.width)
                    max_piece_height = max(max_piece_height, cropped_piece.height)
                
        # If fixed size is requested, use specified dimensions or calculate based on max piece size
        if fixed_size:
            if output_width is None:
                output_width = max_piece_width
            if output_height is None:
                output_height = max_piece_height
            
            print(f"Using fixed output dimensions: {output_width}x{output_height}")
        
        # Save all pieces with proper centering if needed
        for row in range(rows):
            for col in range(cols):
                if (row, col) in piece_images:
                    piece_img = piece_images[(row, col)]
                    
                    # Apply fixed size and centering if requested
                    if fixed_size:
                        piece_img = center_and_resize_image(piece_img, output_width, output_height)
                    
                    # Save the final piece
                    output_path = os.path.join(output_folder, f"{prefix}_{row:02d}_{col:02d}.{format}")
                    piece_img.save(output_path)
                    
                    print(f"Created piece {row+1},{col+1} at {output_path}")
        
        # Optional: Check if the allocation map has any unallocated pixels that should have been allocated
        if debug:
            # Save the allocation map for debugging
            allocation_img = Image.fromarray(allocation_map * 255)
            allocation_img.save(os.path.join(debug_dir, "allocation_map.png"))
        
        print(f"Successfully extracted {rows*cols} puzzle pieces to {output_folder}")
        
    except Exception as e:
        print(f"Error extracting puzzle pieces: {e}")
        import traceback
        traceback.print_exc()
        # Keep debug files if there was an error
        debug = True
    
    finally:
        # Clean up temp files unless debug is True
        if not debug:
            shutil.rmtree(temp_dir)
        else:
            print(f"Debug files saved to {debug_dir if debug_dir else temp_dir}")

def main():
    args = parse_arguments()
    extract_puzzle_pieces(args.image, args.svg, args.output, 
                        args.prefix, args.format, args.padding, 
                        args.fixed_size, args.output_width, args.output_height,
                        args.debug)

if __name__ == "__main__":
    main()