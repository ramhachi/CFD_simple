import os
import sys

def read_params():
    params = {}
    if not os.path.exists("cfd_params.txt"):
        print("Error: cfd_params.txt not found. Run run_cfd.py first.")
        sys.exit(1)
    with open("cfd_params.txt", "r") as f:
        for line in f:
            if '=' in line:
                k, v = line.strip().split('=', 1)
                params[k] = v
    return params

def write_U_file(velocity):
    template = f"""/*--------------------------------*- C++ -*----------------------------------*\\
  =========                 |
  \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox
   \\\\    /   O peration     | Website:  https://openfoam.org
    \\\\  /    A nd           | Version:  11
     \\\\/     M anipulation  |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volVectorField;
    location    "0";
    object      U;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 1 -1 0 0 0 0];

internalField   uniform ({velocity} 0 0);

boundaryField
{{
    inlet
    {{
        type            fixedValue;
        value           uniform ({velocity} 0 0);
    }}
    outlet
    {{
        type            zeroGradient;
    }}
    ground
    {{
        type            fixedValue;
        value           uniform ({velocity} 0 0); // Moving ground
    }}
    topAndSides
    {{
        type            symmetry;
    }}
    "(body.*|tires.*|frame.*)"
    {{
        type            noSlip;
    }}
}}
"""
    with open("0/U", "w") as f:
        f.write(template)

def write_snappyHexMeshDict(aero_stls, use_tires, use_frame, mesh_level):
    
    # 粗さに応じたレベル設定
    if mesh_level == '1':
        level_surf = "3 4"
        level_feat = "3"
        n_layers = 2
    elif mesh_level == '3':
        level_surf = "5 6"
        level_feat = "5"
        n_layers = 5
    else:  # '2' または default
        level_surf = "4 5"
        level_feat = "4"
        n_layers = 3

    stls = aero_stls.split(',')
    if use_tires == '1':
        stls.append("tires.stl")
    if use_frame == '1':
        stls.append("frame.stl")

    geometry_block = ""
    refinement_surfaces_block = ""
    layers_block = ""

    for stl in stls:
        name = stl.split('.')[0]
        geometry_block += f"""
    {stl}
    {{
        type triSurfaceMesh;
        name {name};
    }}"""
        refinement_surfaces_block += f"""
        {name}
        {{
            level ({level_surf});
        }}"""
        
        # フレームにはレイヤーメッシュを入れないなどの工夫も可。今回は全てに適用
        layers_block += f"""
        {name}
        {{
            nSurfaceLayers {n_layers};
        }}"""


    template = f"""/*--------------------------------*- C++ -*----------------------------------*\\
  =========                 |
  \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox
   \\\\    /   O peration     | Website:  https://openfoam.org
    \\\\  /    A nd           | Version:  11
     \\\\/     M anipulation  |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      snappyHexMeshDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

castellatedMesh true;
snap            true;
addLayers       true;

mergeTolerance 1e-6;

geometry
{{
    {geometry_block}
}};

castellatedMeshControls
{{
    maxLocalCells 1000000;
    maxGlobalCells 5000000;
    minRefinementCells 10;
    maxLoadUnbalance 0.10;
    nCellsBetweenLevels 3;

    features
    (
        // eSmack等でeMeshを抽出した場合はここに書く
    );

    refinementSurfaces
    {{
        {refinement_surfaces_block}
    }}

    resolveFeatureAngle 30;

    refinementRegions
    {{
    }}

    locationInMesh (-4.5123 2.5123 3.5123); // 注意: 対象物体の内部にならないよう調整必要
    allowFreeStandingZoneFaces true;
}}

snapControls
{{
    nSmoothPatch 3;
    tolerance 2.0;
    nSolveIter 30;
    nRelaxIter 5;
}}

addLayersControls
{{
    relativeSizes true;
    layers
    {{
        {layers_block}
    }}
    expansionRatio 1.3;
    finalLayerThickness 0.5;
    minThickness 0.1;
    nGrow 0;
    featureAngle 60;
    nRelaxIter 3;
    nSmoothSurfaceNormals 1;
    nSmoothNormals 3;
    nSmoothThickness 10;
    maxFaceThicknessRatio 0.5;
    maxThicknessToMedialRatio 0.3;
    minMedialAxisAngle 90;
    nBufferCellsNoExtrude 0;
    nLayerIter 50;
}}

meshQualityControls
{{
    maxNonOrtho 65;
    maxBoundarySkewness 20;
    maxInternalSkewness 4;
    maxConcave 80;
    minVol 1e-13;
    minTetQuality -1e+30;
    minArea -1;
    minTwist 0.05;
    minDeterminant 0.001;
    minFaceWeight 0.05;
    minVolRatio 0.01;
    triangleTwist -1;
    minTriangleTwist -1;
    nSmoothScale 4;
    errorReduction 0.75;
}}

debug 0;
// ************************************************************************* //
"""
    with open("system/snappyHexMeshDict", "w") as f:
        f.write(template)


if __name__ == "__main__":
    params = read_params()
    velocity = params.get("VELOCITY", "20.0")
    aero_stls = params.get("AERO_STLS", "body.stl")
    use_tires = params.get("USE_TIRES", "0")
    use_frame = params.get("USE_FRAME", "0")
    mesh_level = params.get("MESH_LEVEL", "2")

    print("[Python] Generating OpenFOAM dictionaries...")
    write_U_file(velocity)
    write_snappyHexMeshDict(aero_stls, use_tires, use_frame, mesh_level)
    print("[Python] Done.")
