"""Verify the bundled Caine model stays detailed, portable, and animated."""
import json
from pathlib import Path
import struct


ASSET = Path(__file__).parents[1] / "src" / "autonomous_ai_world" / "web" / "assets" / "caine.glb"


def test_caine_glb_contains_the_full_animation_set_and_embedded_geometry() -> None:
    data = ASSET.read_bytes()
    magic, version, length = struct.unpack_from("<4sII", data)
    assert (magic, version, length) == (b"glTF", 2, len(data))
    chunk_length, chunk_type = struct.unpack_from("<I4s", data, 12)
    assert chunk_type == b"JSON"
    document = json.loads(data[20:20 + chunk_length])

    assert {clip["name"] for clip in document["animations"]} >= {"Idle", "Fly", "Talk", "CheckUp"}
    assert len(document['skins'][0]['joints']) > 30
    primitives = [p for mesh in document['meshes'] for p in mesh['primitives']]
    assert any('JOINTS_0' in p['attributes'] for p in primitives)
    assert any('COLOR_0' in p['attributes'] for p in primitives)
    # Bone-parented eyes can silently disappear during deform-only export.
    names = {n.get('name') for n in document['nodes'] if 'mesh' in n}
    assert {'caine_eyeballL', 'caine_eyeballR', 'caine_teethtop', 'caine_teethbottom'} <= names
    assert all("uri" not in buffer for buffer in document["buffers"])
