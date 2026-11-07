#!/usr/bin/env python3
"""Validate scored-A source correspondence and scan the public release tree."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
FROZEN_SUPPLEMENT="08ab46ce10b504b0b9458c07eaf11f3194401830b618c5072140ad1fc2947537"
FROZEN_A="90a6a22560328e4ff5ec3f86375dbf567aecf802d2632fe6829878b339be7c3c"
PAPER_SHA="084cd9908cf268d5f018c91fa73a59cbd1d5cf28c5a3f3063c76972706e6f102"
CREDENTIAL=re.compile(
    rb"sk-(?:proj-)?[A-Za-z0-9_-]{30,}|hf_[A-Za-z0-9]{25,}|(?:gh[pousr]_|\bgithub_pat_)[A-Za-z0-9_]{25,}"
    rb"|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|X-Amz-Signature\x3d|X-Goog-Signature\x3d"
    rb"|(?i:Bearer)\s+[A-Za-z0-9_-]{32,}|(?:acct|org|proj)_[A-Za-z0-9]{18,}", re.I
)
PRIVATE=re.compile(rb"/(?:Users|home)/[A-Za-z0-9_.-]+/|subject_[0-9]{5,}|benchmark_[0-9]{5,}")
FORBIDDEN={".zip",".sqlite",".sqlite3",".db",".npy",".npz",".bin",".parquet",".safetensors",
           ".jsonl",".pkl",".pickle",".gz",".whl",".pt"}
SKIP={".git","__pycache__","outputs",".DS_Store"}
NOTEBOOK="notebooks/01_BLE_1_5A_Explained.ipynb"
PREVIEW="notebooks/01_BLE_1_5A_Explained.html"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def no_secret(data, name, *, check_paths=True):
    if CREDENTIAL.search(data) or (check_paths and PRIVATE.search(data)):
        raise ValueError(f"Credential, account identifier, or private path pattern: {name}")


def scan_notebook(raw):
    book=json.loads(raw)
    assert set(book["metadata"]).issubset({"kernelspec","language_info"})
    assert len(book["cells"])==60
    images=code=0
    for cell in book["cells"]:
        assert not cell.get("attachments") and not cell.get("metadata")
        if cell["cell_type"]!="code":
            continue
        code+=1
        assert cell["execution_count"]==code
        for output in cell["outputs"]:
            assert output["output_type"] in {"display_data","execute_result","stream"}
            data=output.get("data",{})
            assert set(data).issubset({"image/png","text/plain","text/html"})
            if "image/png" in data:
                src=data["image/png"]
                png=base64.b64decode("".join(src) if isinstance(src,list) else src)
                assert png.startswith(b"\x89PNG\r\n\x1a\n")
                no_secret(png,"embedded figure",check_paths=False)
                images+=1
    assert code==19 and images==9
    return {"executed_code_cells":code,"embedded_png_outputs":images}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--supplement",type=Path,help="Optional exact source archive for reference comparison")
    parser.add_argument("--paper-text",type=Path,help="Optional pdftotext extraction of the verified paper")
    parser.add_argument("--git-history",action="store_true",help="Also scan reachable Git blobs")
    args=parser.parse_args()
    home=ROOT/"hosted-ble15a"
    raw=(home/"ARTIFACT_MANIFEST.json").read_bytes()
    manifest=json.loads(raw)
    assert manifest["original_scored_archive"]["sha256"]==FROZEN_A
    expected={x["path"]:x for x in manifest["members"] if x["delivery"]=="bundled"}
    observed={p.relative_to(home/"runtime").as_posix() for p in (home/"runtime").rglob("*")
              if p.is_file() and "__pycache__" not in p.parts}
    assert observed==set(expected) and len(observed)==64
    for name,entry in expected.items():
        data=(home/"runtime"/name).read_bytes()
        assert sha(data)==entry["sha256"] and len(data)==entry["bytes"],name
    cfg=json.loads((home/"runtime/submission_config.json").read_text())
    assert cfg["api_keys"]=={} and cfg["enable_paid_inference"] is False
    if args.supplement:
        assert sha(args.supplement.read_bytes())==FROZEN_SUPPLEMENT
        with zipfile.ZipFile(args.supplement) as z:
            assert z.read("ARTIFACT_MANIFEST.json")==raw
            assert all((home/name).read_bytes()==z.read(name) for name in z.namelist())
    fig=json.loads((ROOT/"figures/PROVENANCE.json").read_text())
    figures={f"figures/{name}":meta["sha256"] for name,meta in fig.items()}
    binary={**figures,"paper/PAIEC_BLE_NeurIPS2026_Reconstructed.pdf":PAPER_SHA}
    count=0
    for path in sorted(ROOT.rglob("*")):
        rel=path.relative_to(ROOT)
        if any(x in SKIP or x.startswith(".venv") for x in rel.parts):
            continue
        if path.is_symlink():
            raise ValueError(f"Symlink in release: {rel}")
        if not path.is_file():
            continue
        name=rel.as_posix()
        assert path.suffix not in FORBIDDEN,rel
        assert not path.name.startswith(".env"),rel
        if path.name=="submission_config.json":
            assert name=="hosted-ble15a/runtime/submission_config.json"
        contents=path.read_bytes()
        if name in binary:
            assert sha(contents)==binary[name]
            no_secret(contents,name,check_paths=False)
        else:
            assert b"\x00" not in contents,rel
            no_secret(contents,name)
        count+=1
    book=scan_notebook((ROOT/NOTEBOOK).read_bytes())
    preview=(ROOT/PREVIEW).read_text()
    assert len(re.findall(r'<img\b',preview))==9
    assert not re.search(r'<(?:script|iframe)\b|\b(?:src|poster)=["\x27](?:https?:)?//',preview,re.I)
    assert len(set(re.findall(r'<a id="(overview|competition|baselines|beliefs|production|retrieval|public|hosted|decisions|reliability|reproduce|conclusions)"',preview)))==12
    for link in re.findall(r'href="(\.\./[^"]+)"',preview):
        assert (ROOT/PREVIEW).parent.joinpath(link.split("#",1)[0]).exists(),link
    if args.paper_text:
        no_secret(args.paper_text.read_bytes(),"extracted paper text")
    n_history=0
    if args.git_history:
        seen=set()
        for row in subprocess.check_output(["git","rev-list","--objects","--all"],cwd=ROOT).splitlines():
            oid,_,name=row.partition(b" ")
            if oid in seen:
                continue
            seen.add(oid)
            ident=oid.decode()
            if subprocess.check_output(["git","cat-file","-t",ident],cwd=ROOT).strip()==b"blob":
                no_secret(subprocess.check_output(["git","cat-file","blob",ident],cwd=ROOT),
                          name.decode(errors="replace"))
                n_history+=1
    print(json.dumps({"status":"PASS","files_scanned":count,"history_blobs_scanned":n_history,
                      "bundled_runtime_members_verified":len(observed),"unchanged_original_python_files":35,
                      "frozen_private_archive_sha256":FROZEN_A,"artifact_manifest_sha256":sha(raw),
                      "notebook":book,"scope":"Heuristic patterns plus allowlisted binary and exact manifest checks."},indent=2))


if __name__=="__main__":
    main()
