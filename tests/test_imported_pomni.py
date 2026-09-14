"""Verify the shipped binary remains a self-contained, animatable model."""
import json
from pathlib import Path
import struct

ASSETS = Path(__file__).parents[1] / 'src' / 'autonomous_ai_world' / 'web' / 'assets'


def test_pomni_contains_skin_animations_and_embedded_textures():
    data = (ASSETS / 'pomni.glb').read_bytes()
    magic, version, length = struct.unpack_from('<4sII', data)
    assert (magic, version, length) == (b'glTF', 2, len(data))
    chunk_length, chunk_type = struct.unpack_from('<I4s', data, 12)
    assert chunk_type == b'JSON'
    document = json.loads(data[20:20 + chunk_length])
    assert {clip['name'] for clip in document['animations']} >= {'Idle', 'Walk', 'Talk', 'Reach'}
    assert len(document['skins'][0]['joints']) > 20
    assert all('uri' not in buffer for buffer in document['buffers'])
    assert all('bufferView' in image for image in document['images'])
    assert any('Ah' in mesh.get('extras', {}).get('targetNames', []) for mesh in document['meshes'])
    # A regression to rigid decorative primitives should fail this contract.
    assert any('JOINTS_0' in primitive['attributes'] for mesh in document['meshes'] for primitive in mesh['primitives'])
