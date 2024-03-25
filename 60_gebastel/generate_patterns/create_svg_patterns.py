from lxml import etree
from tqdm import tqdm
import math

PT_TO_MM = 0.3527777778

def get_svg_element( block_size ):
    block_size_in_mm = block_size * 0.3527777778

    root = etree.Element('svg')
    root.attrib['x'] = '0mm'
    root.attrib['y'] = '0mm'
    root.attrib['width'] = f'{ block_size_in_mm }mm'
    root.attrib['height'] = f'{ block_size_in_mm }mm'
    # root.attrib['viewBox'] = f'0mm 0mm { block_size_in_mm }mm { block_size_in_mm }mm'
    root.attrib['version'] = '1.1'
    root.attrib['xmlns'] = 'http://www.w3.org/2000/svg'
    #root.attrib['xmlns:xlink'] = 'http://www.w3.org/1999/xlink'

    return root


def create_circles( block_size, line_width, drift_function, margin=5 ):
    root = get_svg_element( block_size + margin * 2 )
    i = 0
    cur_r = block_size / 2 - drift_function(i)

    while cur_r > line_width * 4:
        circle = etree.Element('circle')
        circle.attrib['cx'] = f'{block_size / 2 + margin}pt'
        circle.attrib['cy'] = f'{block_size / 2 + margin}pt'
        circle.attrib['r'] = f'{ cur_r }pt'
        circle.attrib['stroke'] = 'black'
        circle.attrib['stroke-width'] = f'{ line_width }pt'
        circle.attrib['fill'] = 'none'

        root.append( circle )

        i += 1
        cur_r = block_size / 2 - drift_function(i)

    return etree.tostring(root, pretty_print=True)


def create_diamond_line( block_size, line_width, drift_function, diamond_height=10, diamond_width=10 ):
    root = get_svg_element( block_size )
    i = 0
    x = drift_function(i)

    while x < block_size:
        # <polyline points="0,100 50,25 50,75 100,0" />

        j = 0
        y = 0
        while y < block_size:
            is_left_breakout = j % 2 == 0

            line = etree.Element('line')
            line.attrib['x1' if is_left_breakout else 'x2'] = f'{x + diamond_width / 2}pt'
            line.attrib['x2' if is_left_breakout else 'x1'] = f'{x - diamond_width / 2}pt'
            line.attrib['y1'] = f'{y}pt'
            line.attrib['y2'] = f'{y + diamond_height / 2}pt'
            line.attrib['stroke'] = 'black'
            line.attrib['stroke-width'] = f'{ line_width }pt'

            root.append(line)
            y += diamond_height / 2
            j += 1
        
        i += 1
        x = drift_function(i)


    return etree.tostring(root, pretty_print=True)


def create_lines( block_size, line_width, drift_function ):
    root = get_svg_element( block_size )
    i = 0
    x = drift_function(i)

    while x < block_size:
        # <line x1="0" y1="80" x2="100" y2="20" stroke="black" />
        line = etree.Element('line')
        line.attrib['x1'] = f'{x}pt'
        line.attrib['x2'] = f'{x}pt'
        line.attrib['y1'] = '0pt'
        line.attrib['y2'] = f'{block_size}pt'
        line.attrib['stroke'] = 'black'
        line.attrib['stroke-width'] = f'{ line_width }pt'

        root.append(line)
        
        i += 1
        x = drift_function(i)
        print( i, x )


    return etree.tostring(root, pretty_print=True)



if __name__ == '__main__':
    block_sizes = {
        '20mm' : 20 / PT_TO_MM,
        '40mm' : 40 / PT_TO_MM,
        '200mm' : 200 / PT_TO_MM
    }

    screen_rulings = {
        '150lpi' : 72 / 150,
        '175lpi' : 72 / 175
    }

    # for i in tqdm(range(10)):
    #     line_width = screen_rulings['150lpi'] * ((i+1) / 10)

    #     with open(f'../20_svgs/lines_150lpi_{ str(i) }.svg','wb') as svg_file:
    #         # gleichmäßige Rasterweite
    #         svg_file.write(
    #             create_lines( block_sizes['200mm'], line_width, lambda i: i * screen_rulings['150lpi'] )
    #         )


    for i in tqdm(range(10)):

        with open(f'../20_svgs/lines_150lpi_vorschub_{ str(i) }.svg','wb') as svg_file:
            # gleichmäßige Rasterweite
            svg_file.write(
                create_lines( block_sizes['200mm'], screen_rulings['150lpi'], lambda i: (i * 5 + math.sqrt(i)) * screen_rulings['150lpi'] )
            )


    # for i in tqdm(range(10)):
    #     line_width = screen_rulings['150lpi'] * ((i+1) / 10)

    #     with open(f'../20_svgs/diamons_150lpi_straight_{ str(i) }.svg','wb') as svg_file:
    #         # gleichmäßige Rasterweite
    #         svg_file.write(
    #             create_diamond_line( block_sizes['200mm'], line_width, lambda i: i * screen_rulings['150lpi'] )
    #         )