import struct
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT_DIR / 'models'


def write_binary_stl(path: Path, triangles):
    header = b'CFD_simple generated STL'.ljust(80, b' ')
    with path.open('wb') as handle:
        handle.write(header)
        handle.write(struct.pack('<I', len(triangles)))
        for normal, vertices in triangles:
            handle.write(struct.pack('<3f', *normal))
            for vertex in vertices:
                handle.write(struct.pack('<3f', *vertex))
            handle.write(struct.pack('<H', 0))


def create_box(path: Path, size_x: float, size_y: float, size_z: float, offset=(0.0, 0.0, 0.0)):
    ox, oy, oz = offset
    x0, x1 = ox - size_x / 2.0, ox + size_x / 2.0
    y0, y1 = oy - size_y / 2.0, oy + size_y / 2.0
    z0, z1 = oz - size_z / 2.0, oz + size_z / 2.0
    vertices = [
        (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
        (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
    ]
    faces = [
        ((0.0, 0.0, -1.0), (0, 2, 1)), ((0.0, 0.0, -1.0), (0, 3, 2)),
        ((0.0, 0.0, 1.0), (4, 5, 6)), ((0.0, 0.0, 1.0), (4, 6, 7)),
        ((0.0, -1.0, 0.0), (0, 1, 5)), ((0.0, -1.0, 0.0), (0, 5, 4)),
        ((0.0, 1.0, 0.0), (3, 7, 6)), ((0.0, 1.0, 0.0), (3, 6, 2)),
        ((-1.0, 0.0, 0.0), (0, 4, 7)), ((-1.0, 0.0, 0.0), (0, 7, 3)),
        ((1.0, 0.0, 0.0), (1, 2, 6)), ((1.0, 0.0, 0.0), (1, 6, 5)),
    ]
    triangles = [(normal, [vertices[a], vertices[b], vertices[c]]) for normal, (a, b, c) in faces]
    write_binary_stl(path, triangles)


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    create_box(OUTPUT_DIR / 'body.stl', 1.0, 0.45, 0.35, offset=(0.6, 0.0, 0.175))
    create_box(OUTPUT_DIR / 'tires.stl', 0.20, 0.16, 0.16, offset=(0.0, 0.0, 0.08))
    create_box(OUTPUT_DIR / 'frame.stl', 0.90, 0.10, 0.15, offset=(0.55, 0.0, 0.20))
    print(f'Sample STL files were written to: {OUTPUT_DIR}')


if __name__ == '__main__':
    main()
