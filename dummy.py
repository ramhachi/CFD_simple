import numpy as np
from stl import mesh

def create_box(filename, width, height, depth, offset_x=0, offset_y=0, offset_z=0):
    vertices = np.array([\
        [-1, -1, -1],\
        [+1, -1, -1],\
        [+1, +1, -1],\
        [-1, +1, -1],\
        [-1, -1, +1],\
        [+1, -1, +1],\
        [+1, +1, +1],\
        [-1, +1, +1]]) * np.array([width/2, depth/2, height/2]) + np.array([offset_x, offset_y, offset_z])

    faces = np.array([\
        [0,3,1], [1,3,2], [0,4,7], [0,7,3], [4,5,6],\
        [4,6,7], [5,1,2], [5,2,6], [2,3,6], [3,7,6],\
        [0,1,5], [0,5,4]])

    cube = mesh.Mesh(np.zeros(faces.shape[0], dtype=mesh.Mesh.dtype))
    for i, f in enumerate(faces):
        for j in range(3):
            cube.vectors[i][j] = vertices[f[j],:]
    cube.save(filename)

create_box('body.stl', 1, 0.5, 0.5, 1, 0, 0.5)
create_box('tires.stl', 0.2, 0.5, 0.2, 0, 0, 0.2)
create_box('frame.stl', 0.8, 0.2, 0.2, 1, 0, 0.5)
