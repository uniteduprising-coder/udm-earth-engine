from earth.projection.udm import PHI_NODE_DEG, PHI_WIND_DEG, project_flat, winding_function


def test_winding_at_equator():
    w = winding_function(0)
    assert abs(w - 0.332984) < 0.01


def test_winding_at_wind_center():
    w = winding_function(PHI_WIND_DEG)
    assert abs(w - 1.0) < 0.001


def test_flat_projection_differs_from_wgs84():
    udm = project_flat(38.25, -85.76, mode="udm_flat")
    wgs = project_flat(38.25, -85.76, mode="wgs84")
    assert udm["lat_udm"] != wgs["lat_udm"] or udm["lon_udm"] != wgs["lon_udm"]


def test_node_pull_toward_bloch():
    north = project_flat(45.0, -90.0, mode="udm_flat")
    assert north["lat_udm"] < 45.0  # pulled toward PHI_NODE_DEG