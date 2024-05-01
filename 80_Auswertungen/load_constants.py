import json
from pathlib import Path

def load_colors():
    color_json_path = Path( __file__ ).parent / 'colors.json'

    with color_json_path.open() as json_file:
        colors = json.load( json_file )

    if 'True' in colors['COLOR_MAP']:
        colors['COLOR_MAP'][True] = colors['COLOR_MAP']['True']

    if 'False' in colors['COLOR_MAP']:
        colors['COLOR_MAP'][False] = colors['COLOR_MAP']['False']

    return colors

if __name__ == '__main__':
    print( load_colors() )