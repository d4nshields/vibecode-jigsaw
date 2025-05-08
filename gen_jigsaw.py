#!/usr/bin/env python3

import argparse
import math
import random


class JigsawGenerator:
    def __init__(self, width, height, xn, yn, tab_size, jitter, seed, corner_radius):
        self.width = width
        self.height = height
        self.xn = xn
        self.yn = yn
        self.t = tab_size / 200.0
        self.j = jitter / 100.0
        self.seed = seed
        self.corner_radius = corner_radius
        self.offset = 0.0
        
        # Initialize variables needed for puzzle generation
        self.a = 0
        self.b = 0
        self.c = 0
        self.d = 0
        self.e = 0
        self.flip = False
        self.xi = 0
        self.yi = 0
        self.vertical = False
        
        # Set random seed
        random.seed(self.seed)
        
    def random(self):
        """Replacement for the JavaScript random function based on sine"""
        x = math.sin(self.seed) * 10000
        self.seed += 1
        return x - math.floor(x)
    
    def uniform(self, min_val, max_val):
        """Generate a random number in the range [min_val, max_val]"""
        r = self.random()
        return min_val + r * (max_val - min_val)
    
    def rbool(self):
        """Random boolean"""
        return self.random() > 0.5
    
    def first(self):
        """Initialize the first tab"""
        self.e = self.uniform(-self.j, self.j)
        self.next()
        
    def next(self):
        """Calculate parameters for the next tab"""
        flip_old = self.flip
        self.flip = self.rbool()
        self.a = -self.e if self.flip == flip_old else self.e
        self.b = self.uniform(-self.j, self.j)
        self.c = self.uniform(-self.j, self.j)
        self.d = self.uniform(-self.j, self.j)
        self.e = self.uniform(-self.j, self.j)
    
    def sl(self):
        """Segment length"""
        return self.height / self.yn if self.vertical else self.width / self.xn
    
    def sw(self):
        """Segment width"""
        return self.width / self.xn if self.vertical else self.height / self.yn
    
    def ol(self):
        """Offset length"""
        return self.offset + self.sl() * (self.yi if self.vertical else self.xi)
    
    def ow(self):
        """Offset width"""
        return self.offset + self.sw() * (self.xi if self.vertical else self.yi)
    
    def l(self, v):
        """Calculate length coordinate"""
        ret = self.ol() + self.sl() * v
        return round(ret * 100) / 100
    
    def w(self, v):
        """Calculate width coordinate"""
        multiplier = -1.0 if self.flip else 1.0
        ret = self.ow() + self.sw() * v * multiplier
        return round(ret * 100) / 100
    
    # Points for the Bezier curves
    def p0l(self): return self.l(0.0)
    def p0w(self): return self.w(0.0)
    def p1l(self): return self.l(0.2)
    def p1w(self): return self.w(self.a)
    def p2l(self): return self.l(0.5 + self.b + self.d)
    def p2w(self): return self.w(-self.t + self.c)
    def p3l(self): return self.l(0.5 - self.t + self.b)
    def p3w(self): return self.w(self.t + self.c)
    def p4l(self): return self.l(0.5 - 2.0 * self.t + self.b - self.d)
    def p4w(self): return self.w(3.0 * self.t + self.c)
    def p5l(self): return self.l(0.5 + 2.0 * self.t + self.b - self.d)
    def p5w(self): return self.w(3.0 * self.t + self.c)
    def p6l(self): return self.l(0.5 + self.t + self.b)
    def p6w(self): return self.w(self.t + self.c)
    def p7l(self): return self.l(0.5 + self.b + self.d)
    def p7w(self): return self.w(-self.t + self.c)
    def p8l(self): return self.l(0.8)
    def p8w(self): return self.w(self.e)
    def p9l(self): return self.l(1.0)
    def p9w(self): return self.w(0.0)
    
    def gen_dh(self):
        """Generate horizontal dividers"""
        paths = []
        self.vertical = False
        
        for self.yi in range(1, self.yn):
            self.xi = 0
            self.first()
            path = f"M {self.p0l()},{self.p0w()} "
            
            for self.xi in range(0, self.xn):
                path += (f"C {self.p1l()} {self.p1w()} {self.p2l()} {self.p2w()} "
                         f"{self.p3l()} {self.p3w()} ")
                path += (f"C {self.p4l()} {self.p4w()} {self.p5l()} {self.p5w()} "
                         f"{self.p6l()} {self.p6w()} ")
                path += (f"C {self.p7l()} {self.p7w()} {self.p8l()} {self.p8w()} "
                         f"{self.p9l()} {self.p9w()} ")
                self.next()
            
            paths.append(path)
        
        return "".join(paths)
    
    def gen_dv(self):
        """Generate vertical dividers"""
        paths = []
        self.vertical = True
        
        for self.xi in range(1, self.xn):
            self.yi = 0
            self.first()
            path = f"M {self.p0w()},{self.p0l()} "
            
            for self.yi in range(0, self.yn):
                path += (f"C {self.p1w()} {self.p1l()} {self.p2w()} {self.p2l()} "
                         f"{self.p3w()} {self.p3l()} ")
                path += (f"C {self.p4w()} {self.p4l()} {self.p5w()} {self.p5l()} "
                         f"{self.p6w()} {self.p6l()} ")
                path += (f"C {self.p7w()} {self.p7l()} {self.p8w()} {self.p8l()} "
                         f"{self.p9w()} {self.p9l()} ")
                self.next()
            
            paths.append(path)
        
        return "".join(paths)
    
    def gen_db(self):
        """Generate border"""
        path = f"M {self.offset + self.corner_radius} {self.offset} "
        path += f"L {self.offset + self.width - self.corner_radius} {self.offset} "
        path += (f"A {self.corner_radius} {self.corner_radius} 0 0 1 "
                 f"{self.offset + self.width} {self.offset + self.corner_radius} ")
        path += f"L {self.offset + self.width} {self.offset + self.height - self.corner_radius} "
        path += (f"A {self.corner_radius} {self.corner_radius} 0 0 1 "
                 f"{self.offset + self.width - self.corner_radius} {self.offset + self.height} ")
        path += f"L {self.offset + self.corner_radius} {self.offset + self.height} "
        path += (f"A {self.corner_radius} {self.corner_radius} 0 0 1 "
                 f"{self.offset} {self.offset + self.height - self.corner_radius} ")
        path += f"L {self.offset} {self.offset + self.corner_radius} "
        path += (f"A {self.corner_radius} {self.corner_radius} 0 0 1 "
                 f"{self.offset + self.corner_radius} {self.offset} ")
        
        return path
    
    def generate_svg(self):
        """Generate the complete SVG file content"""
        # Reset seed to ensure consistent results
        random.seed(self.seed)
        self.seed = self.seed
        
        # SVG header
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" version="1.0" '
               f'width="{self.width}mm" height="{self.height}mm" '
               f'viewBox="0 0 {self.width} {self.height}">')
        
        # Horizontal dividers
        svg += (f'<path fill="none" stroke="Black" stroke-width="1.0" d="'
                f'{self.gen_dh()}'
                f'"></path>')
        
        # Vertical dividers
        svg += (f'<path fill="none" stroke="Black" stroke-width="1.0" d="'
                f'{self.gen_dv()}'
                f'"></path>')
        
        # Border
        svg += (f'<path fill="none" stroke="Black" stroke-width="1.0" d="'
                f'{self.gen_db()}'
                f'"></path>')
        
        svg += '</svg>'
        return svg


def main():
    parser = argparse.ArgumentParser(description='Generate a jigsaw puzzle SVG file')
    parser.add_argument('--grid', nargs=2, type=int, default=[15, 10], metavar=('COLS', 'ROWS'),
                        help='Number of columns and rows (default: 15 10)')
    parser.add_argument('-o', '--output', type=str, default='jigsaw.svg',
                        help='Output SVG file (default: jigsaw.svg)')
    parser.add_argument('--jitter', type=float, default=4.0,
                        help='Jitter percentage (default: 4.0)')
    parser.add_argument('--tabsize', type=float, default=20.0,
                        help='Tab size percentage (default: 20.0)')
    parser.add_argument('--seed', type=int, default=None,
                        help='Random seed (default: random)')
    parser.add_argument('--width', type=int, default=300,
                        help='Width in mm (default: 300)')
    parser.add_argument('--height', type=int, default=200,
                        help='Height in mm (default: 200)')
    parser.add_argument('--radius', type=float, default=2.0,
                        help='Corner radius in mm (default: 2.0)')
    
    args = parser.parse_args()
    
    # Use current time as seed if none provided
    if args.seed is None:
        args.seed = int(random.random() * 10000)
    
    # Create jigsaw generator
    jigsaw = JigsawGenerator(
        width=args.width,
        height=args.height,
        xn=args.grid[0],
        yn=args.grid[1],
        tab_size=args.tabsize,
        jitter=args.jitter,
        seed=args.seed,
        corner_radius=args.radius
    )
    
    # Generate SVG content
    svg_content = jigsaw.generate_svg()
    
    # Save to file
    with open(args.output, 'w') as f:
        f.write(svg_content)
    
    print(f"Jigsaw puzzle saved to {args.output}")
    print(f"Dimensions: {args.width}mm x {args.height}mm")
    print(f"Grid: {args.grid[0]} x {args.grid[1]}")
    print(f"Seed: {args.seed}")


if __name__ == "__main__":
    main()