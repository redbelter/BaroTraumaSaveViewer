# Check what gamesession content actually is
import gzip, io, pathlib

path = pathlib.Path("data/samples/grav.save")
data = path.read_bytes()
buf = io.BytesIO(data)
with gzip.GzipFile(fileobj=buf) as gz:
    level0 = gz.read()

# Extract files
i = 0
while i + 4 <= len(level0):
    name_len = int.from_bytes(level0[i:i+4], "little")
    if name_len < 0 or name_len > 10000 or i + name_len * 2 > len(level0):
        break
    i += 4
    name = level0[i:i+name_len*2].decode("utf-16-le", errors="replace")
    i += name_len * 2
    if i + 4 > len(level0):
        break
    content_len = int.from_bytes(level0[i:i+4], "little")
    if content_len < 0 or content_len > 100_000_000 or i + 4 + content_len > len(level0):
        break
    i += 4
    content = level0[i:i+content_len]
    i += content_len
    
    if "gamesession" in name.lower() or "character" in name.lower():
        print(f"\n=== {name} ===")
        print(f"Content length: {len(content)}")
        print(f"First 500 bytes (hex): {content[:100].hex()}")
        
        # Try decompressing
        try:
            buf2 = io.BytesIO(content)
            with gzip.GzipFile(fileobj=buf2) as gz2:
                decomp = gz2.read()
            print(f"Decompressed: {len(decomp)} bytes")
            print(f"First 300 chars of decompressed: {decomp[:300].decode('utf-8', errors='ignore')}")
        except Exception as e:
            print(f"Decompress failed: {e}")
            # It might be raw text
            text = content.decode("utf-8", errors="ignore")[:500]
            print(f"Raw text: {text}")
