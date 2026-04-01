import os
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


def read_params():
    params = {}
    params_path = ROOT_DIR / 'cfd_params.txt'
    if not params_path.exists():
        print('Error: cfd_params.txt not found. Run run_cfd.py first.')
        sys.exit(1)
    with params_path.open('r', encoding='utf-8') as handle:
        for line in handle:
            if '=' in line:
                key, value = line.strip().split('=', 1)
                params[key] = value
    return params


def parse_csv(value: str):
    return [item for item in value.split(',') if item]


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding='utf-8')


def build_surface_boundary_block(surface_names, patch_type: str, value: str = None) -> str:
    blocks = []
    for surface_name in surface_names:
        lines = [
            f"    {surface_name}",
            "    {",
            f"        type            {patch_type};",
        ]
        if value is not None:
            lines.append(f"        value           uniform {value};")
        lines.append("    }")
        blocks.append('\n'.join(lines))
    return '\n'.join(blocks)


def write_blockMeshDict(params):
    xmin = params.get('DOM_XMIN', '-5')
    xmax = params.get('DOM_XMAX', '10')
    ymin = params.get('DOM_YMIN', '-3')
    ymax = params.get('DOM_YMAX', '3')
    zmin = params.get('DOM_ZMIN', '0')
    zmax = params.get('DOM_ZMAX', '4')
    nx = params.get('NX', '30')
    ny = params.get('NY', '20')
    nz = params.get('NZ', '15')

    content = f"""/*--------------------------------*- C++ -*----------------------------------*\\
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
    object      blockMeshDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

scale   1;

vertices
(
    ({xmin} {ymin} {zmin})
    ({xmax} {ymin} {zmin})
    ({xmax} {ymax} {zmin})
    ({xmin} {ymax} {zmin})
    ({xmin} {ymin} {zmax})
    ({xmax} {ymin} {zmax})
    ({xmax} {ymax} {zmax})
    ({xmin} {ymax} {zmax})
);

blocks
(
    hex (0 1 2 3 4 5 6 7) ({nx} {ny} {nz}) simpleGrading (1 1 1)
);

edges
(
);

boundary
(
    inlet
    {{
        type patch;
        faces
        (
            (0 4 7 3)
        );
    }}
    outlet
    {{
        type patch;
        faces
        (
            (1 2 6 5)
        );
    }}
    ground
    {{
        type wall;
        faces
        (
            (0 3 2 1)
        );
    }}
    topAndSides
    {{
        type symmetry;
        faces
        (
            (4 5 6 7)
            (0 1 5 4)
            (3 7 6 2)
        );
    }}
);

mergePatchPairs
(
);

// ************************************************************************* //
"""
    write_text(ROOT_DIR / 'system' / 'blockMeshDict', content)


def write_U_file(velocity, surface_names):
    surface_block = build_surface_boundary_block(surface_names, 'noSlip')
    content = f"""/*--------------------------------*- C++ -*----------------------------------*\\
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
    location    \"0\";
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
        value           uniform ({velocity} 0 0);
    }}
    topAndSides
    {{
        type            symmetry;
    }}
{surface_block}
}}
"""
    write_text(ROOT_DIR / '0' / 'U', content)


def write_p_file(surface_names):
    surface_block = build_surface_boundary_block(surface_names, 'zeroGradient')
    content = """/*--------------------------------*- C++ -*----------------------------------*\\
  =========                 |
  \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox
   \\    /   O peration     | Website:  https://openfoam.org
    \\  /    A nd           | Version:  11
     \\/     M anipulation  |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    \"0\";
    object      p;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -2 0 0 0 0];

internalField   uniform 0;

boundaryField
{
    inlet
    {
        type            zeroGradient;
    }
    outlet
    {
        type            fixedValue;
        value           uniform 0;
    }
    ground
    {
        type            zeroGradient;
    }
    topAndSides
    {
        type            symmetry;
    }
""" + surface_block + """
}

// ************************************************************************* //
"""
    write_text(ROOT_DIR / '0' / 'p', content)


def write_k_file(k_value, surface_names):
    surface_block = build_surface_boundary_block(surface_names, 'kqRWallFunction', k_value)
    content = f"""/*--------------------------------*- C++ -*----------------------------------*\\
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
    class       volScalarField;
    location    \"0\";
    object      k;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -2 0 0 0 0];

internalField   uniform {k_value};

boundaryField
{{
    inlet
    {{
        type            fixedValue;
        value           uniform {k_value};
    }}
    outlet
    {{
        type            zeroGradient;
    }}
    ground
    {{
        type            kqRWallFunction;
        value           uniform {k_value};
    }}
    topAndSides
    {{
        type            symmetry;
    }}
{surface_block}
}}

// ************************************************************************* //
"""
    write_text(ROOT_DIR / '0' / 'k', content)


def write_omega_file(omega_value, surface_names):
    surface_block = build_surface_boundary_block(surface_names, 'omegaWallFunction', omega_value)
    content = f"""/*--------------------------------*- C++ -*----------------------------------*\\
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
    class       volScalarField;
    location    \"0\";
    object      omega;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 0 -1 0 0 0 0];

internalField   uniform {omega_value};

boundaryField
{{
    inlet
    {{
        type            fixedValue;
        value           uniform {omega_value};
    }}
    outlet
    {{
        type            zeroGradient;
    }}
    ground
    {{
        type            omegaWallFunction;
        value           uniform {omega_value};
    }}
    topAndSides
    {{
        type            symmetry;
    }}
{surface_block}
}}

// ************************************************************************* //
"""
    write_text(ROOT_DIR / '0' / 'omega', content)


def write_nut_file(surface_names):
    surface_block = build_surface_boundary_block(surface_names, 'nutkWallFunction', '0')
    content = """/*--------------------------------*- C++ -*----------------------------------*\\
  =========                 |
  \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox
   \\    /   O peration     | Website:  https://openfoam.org
    \\  /    A nd           | Version:  11
     \\/     M anipulation  |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    \"0\";
    object      nut;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -1 0 0 0 0];

internalField   uniform 0;

boundaryField
{
    inlet
    {
        type            calculated;
        value           uniform 0;
    }
    outlet
    {
        type            calculated;
        value           uniform 0;
    }
    ground
    {
        type            nutkWallFunction;
        value           uniform 0;
    }
    topAndSides
    {
        type            symmetry;
    }
""" + surface_block + """
}

// ************************************************************************* //
"""
    write_text(ROOT_DIR / '0' / 'nut', content)


def write_snappyHexMeshDict(surface_names, frame_names, mesh_level, loc_x, loc_y, loc_z):
    settings = {
        '1': {'surface_level': '2 3', 'feature_level': '2', 'layers': 2},
        '2': {'surface_level': '3 4', 'feature_level': '3', 'layers': 3},
        '3': {'surface_level': '4 5', 'feature_level': '4', 'layers': 5},
    }[mesh_level]

    geometry_block = []
    refinement_block = []
    layers_block = []

    frame_set = set(frame_names)
    for surface_name in surface_names:
        geometry_block.append(
            f"""
    {surface_name}.stl
    {{
        type triSurfaceMesh;
        name {surface_name};
    }}"""
        )
        refinement_block.append(
            f"""
        {surface_name}
        {{
            level ({settings['surface_level']});
        }}"""
        )
        layer_count = 0 if surface_name in frame_set else settings['layers']
        layers_block.append(
            f"""
        {surface_name}
        {{
            nSurfaceLayers {layer_count};
        }}"""
        )

    content = f"""/*--------------------------------*- C++ -*----------------------------------*\\
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
{''.join(geometry_block)}
}};

castellatedMeshControls
{{
    maxLocalCells 1000000;
    maxGlobalCells 5000000;
    minRefinementCells 0;
    maxLoadUnbalance 0.10;
    nCellsBetweenLevels 2;

    features
    (
    );

    refinementSurfaces
    {{
{''.join(refinement_block)}
    }}

    resolveFeatureAngle 45;

    refinementRegions
    {{
    }}

    locationInMesh ({loc_x} {loc_y} {loc_z});
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
{''.join(layers_block)}
    }}
    expansionRatio 1.2;
    finalLayerThickness 0.4;
    minThickness 0.05;
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
    write_text(ROOT_DIR / 'system' / 'snappyHexMeshDict', content)


def write_controlDict(surface_names, velocity, l_ref, a_ref, cofr):
    patches = ' '.join(surface_names)
    cofr_str = f"{cofr[0]} {cofr[1]} {cofr[2]}"
    content = f"""/*--------------------------------*- C++ -*----------------------------------*\\
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
    location    \"system\";
    object      controlDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

application     simpleFoam;

startFrom       startTime;
startTime       0;

stopAt          endTime;
endTime         300;

deltaT          1;
writeControl    timeStep;
writeInterval   20;

purgeWrite      0;
writeFormat     ascii;
writePrecision  6;
writeCompression off;
timeFormat      general;
timePrecision   6;
runTimeModifiable true;

functions
{{
    forces_all
    {{
        type            forces;
        libs            (forces);
        writeControl    timeStep;
        writeInterval   1;

        patches         ( {patches} );
        rho             rhoInf;
        rhoInf          1.225;
        CofR            ({cofr_str});
    }}

    forceCoeffs_all
    {{
        type            forceCoeffs;
        libs            (forces);
        writeControl    timeStep;
        writeInterval   1;

        patches         ( {patches} );
        rho             rhoInf;
        rhoInf          1.225;
        CofR            ({cofr_str});
        liftDir         (0 0 1);
        dragDir         (1 0 0);
        pitchAxis       (0 1 0);

        magUInf         {velocity};
        lRef            {l_ref};
        Aref            {a_ref};
    }}
}}
// ************************************************************************* //
"""
    write_text(ROOT_DIR / 'system' / 'controlDict', content)


if __name__ == '__main__':
    params = read_params()
    velocity = params.get('VELOCITY', '20.0')
    surface_names = parse_csv(params.get('SURFACE_STLS', params.get('AERO_STLS', 'body')))
    frame_names = parse_csv(params.get('FRAME_STLS', ''))
    mesh_level = params.get('MESH_LEVEL', '2')
    loc_x = params.get('LOC_X', '-4.5')
    loc_y = params.get('LOC_Y', '2.5')
    loc_z = params.get('LOC_Z', '3.5')
    l_ref = params.get('L_REF', '1.5')
    a_ref = params.get('A_REF', '1.0')
    cofr = (
        params.get('COFR_X', '0'),
        params.get('COFR_Y', '0'),
        params.get('COFR_Z', '0'),
    )
    turbulence_k = params.get('TURBULENCE_K', '0.24')
    turbulence_omega = params.get('TURBULENCE_OMEGA', '1.78')

    print('[Python] Generating OpenFOAM dictionaries...')
    write_blockMeshDict(params)
    write_U_file(velocity, surface_names)
    write_p_file(surface_names)
    write_k_file(turbulence_k, surface_names)
    write_omega_file(turbulence_omega, surface_names)
    write_nut_file(surface_names)
    write_snappyHexMeshDict(surface_names, frame_names, mesh_level, loc_x, loc_y, loc_z)
    write_controlDict(surface_names, velocity, l_ref, a_ref, cofr)
    print('[Python] Done.')
