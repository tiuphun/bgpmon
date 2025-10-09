import os
import bz2
import tempfile
import pybgpstream

# ====== Configuration ======
TARGET_ASNS = set(["3462", "4780", "1659", "7539", "9924"])  # replace with your target ASNs

ROOT_DIR = "."  # root where collector folders live
OUTPUT_DIR = "extracted_prefixes"
DECOMPRESS_FIRST = False  # whether to write a full decompressed file first (if True) or decompress to temp file

# ====== Utilities ======

def ensure_dir(path):
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)

def iterate_rib_bz2_files(root_dir):
    """
    Yield tuples (collector_name, full_path) for each .bz2 file under collector subfolders.
    """
    for entry in os.listdir(root_dir):
        entry_path = os.path.join(root_dir, entry)
        if os.path.isdir(entry_path):
            collector = entry
            for fname in os.listdir(entry_path):
                if fname.startswith("rib") and fname.endswith(".bz2"):
                    yield collector, os.path.join(entry_path, fname)

def decompress_bz2_to_tempfile(bz2_path):
    tmp = tempfile.NamedTemporaryFile(delete=False)
    with bz2.open(bz2_path, "rb") as fin, open(tmp.name, "wb") as fout:
        while True:
            chunk = fin.read(8192)
            if not chunk:
                break
            fout.write(chunk)
    return tmp.name

def extract_prefixes_from_plain_rib(rib_plain_path, target_asns):
    """
    Given a path to a plain MRT RIB file, parse with a fresh BGPStream and return a set of prefixes.
    """
    prefixes = set()
    # make a fresh BGPStream instance each time
    stream = pybgpstream.BGPStream()
    stream.set_data_interface("singlefile")
    stream.set_data_interface_option("singlefile", "rib-file", rib_plain_path)
    # optionally, you can add filters (if pybgpstream supports filter prior to start)
    # e.g. stream.add_filter("prefix-any", "0.0.0.0/0")
    stream.start()

    # iterate records
    for rec in stream.records():
        if rec.type != "RIB":
            continue
        for elem in rec:
            if elem.type != "R":
                continue
            fields = elem.fields
            prefix = fields.get("prefix")
            aspath = fields.get("as-path") or ""
            if not prefix or not aspath:
                continue
            origin = aspath.strip().split()[-1]
            if origin in target_asns:
                prefixes.add(prefix)
    return prefixes

# ====== Main ======

def main():
    ensure_dir(OUTPUT_DIR)
    for collector, bz2_path in iterate_rib_bz2_files(ROOT_DIR):
        print(f"Processing {collector} {bz2_path}")
        # derive output file name
        base = os.path.basename(bz2_path).replace(".bz2", "")
        output_fname = f"prefixes_{collector}_{base}.txt"
        output_path = os.path.join(OUTPUT_DIR, output_fname)

        # decompress to plain file (temp) or read directly
        if DECOMPRESS_FIRST:
            rib_plain = decompress_bz2_to_tempfile(bz2_path)
        else:
            rib_plain = decompress_bz2_to_tempfile(bz2_path)

        prefixes = set()
        try:
            prefixes = extract_prefixes_from_plain_rib(rib_plain, TARGET_ASNS)
        except Exception as e:
            print("  ERROR parsing RIB:", rib_plain, e)
            # We may choose to skip or write empty
            prefixes = set()

        # write out
        try:
            with open(output_path, "w") as outf:
                for p in sorted(prefixes):
                    outf.write(p + "\n")
            print("  Wrote", len(prefixes), "prefixes to", output_path)
        except Exception as e:
            print("  ERROR writing output:", e)

        # cleanup temp file if needed
        if not DECOMPRESS_FIRST:
            try:
                os.remove(rib_plain)
            except Exception:
                pass

if __name__ == "__main__":
    main()
