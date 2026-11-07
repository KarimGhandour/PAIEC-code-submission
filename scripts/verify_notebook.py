#!/usr/bin/env python3
"""Execute the offline notebook in a fresh IPC kernel and render a standalone HTML."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time

import nbformat
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager
from nbclient import NotebookClient
from nbconvert import HTMLExporter

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks/01_BLE_1_5A_Explained.ipynb"
STYLE = """
:root { color-scheme: light; --ink:#172843; --teal:#147f79; --line:#e3e9ef; }
* { box-sizing:border-box; }
body { background:#edf2f6; color:var(--ink); margin:0; font:16px/1.65 system-ui,sans-serif; }
main { background:white; width:min(1150px,100%); margin:auto; padding:42px clamp(18px,5vw,64px) 76px; }
header { border-bottom:2px solid var(--teal); padding:0 0 12px; letter-spacing:.15em; text-transform:uppercase; font-weight:700; font-size:12px; }
h1 { font-size:clamp(27px,4vw,47px); line-height:1.12; letter-spacing:-.028em; margin:.5em 0; }
h2 { font-size:27px; line-height:1.2; margin:1.8em 0 .55em; border-top:1px solid var(--line); padding-top:24px; }
h3 { font-size:20px; line-height:1.3; }
a { color:#265b8d; text-underline-offset:.16em; }
p { max-width:82ch; }
table { border-collapse:collapse; width:auto; max-width:100%; margin:16px 0 22px; font-size:14px; }
th { background:#eaf1f6; text-align:left; color:var(--ink); }
th,td { border-bottom:1px solid var(--line); padding:9px 12px; vertical-align:top; text-align:left; }
tr:nth-child(even) td { background:#f8fafc; }
pre { white-space:pre-wrap; overflow-wrap:anywhere; font:12.5px/1.58 ui-monospace,monospace; padding:13px 16px; margin:8px 0; }
.input_area { background:#f1f5f9; border:1px solid #dfe8f0; border-left:4px solid #386d9c; border-radius:7px; }
.output_area { overflow-x:auto; }
.output_text { background:#f6faf9; border-left:4px solid var(--teal); }
.prompt,.anchor-link { display:none; }
img { display:block; max-width:100%; height:auto; margin:10px 0 14px; }
.highlight .k,.highlight .kn { color:#684e91; font-weight:600; }
.highlight .s,.highlight .s2 { color:#147f79; }
.highlight .c1 { color:#64778a; }
.cell { margin:0 0 18px; }
@media print { body { background:white; } main { padding:0; } img,pre { break-inside:avoid; } }
"""


def offline_environment(temporary):
    env = {
        "HOME": str(temporary / "home"),
        "TMPDIR": str(temporary / "tmp"),
        "PATH": os.defpath,
        "LANG": "en_US.UTF-8",
        "JUPYTER_CONFIG_DIR": str(temporary / "config"),
        "JUPYTER_RUNTIME_DIR": str(temporary / "runtime"),
        "IPYTHONDIR": str(temporary / "ipython"),
        "MPLCONFIGDIR": str(temporary / "matplotlib"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
    }
    for key in ("HOME", "TMPDIR", "JUPYTER_RUNTIME_DIR"):
        Path(env[key]).mkdir()
    return env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs/notebook")
    args = parser.parse_args()
    started = time.monotonic()
    book = nbformat.read(NOTEBOOK, as_version=4)
    nbformat.validate(book)
    for cell in book.cells:
        if cell.cell_type == "code":
            cell.outputs = []
            cell.execution_count = None
    with tempfile.TemporaryDirectory(prefix="paiec-kernel-") as tmp:
        temporary = Path(tmp)
        kernels = temporary / "kernels"
        kernel = kernels / "paiec-offline"
        kernel.mkdir(parents=True)
        (kernel / "kernel.json").write_text(json.dumps({
            "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
            "display_name": "PAIEC offline", "language": "python"
        }))
        manager = KernelManager(transport="ipc", ip=str(temporary / "ipc"),
                                kernel_name="paiec-offline",
                                kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(kernels)]))
        client = NotebookClient(book, km=manager, kernel_name="paiec-offline",
                                timeout=90, resources={"metadata":{"path":str(ROOT)}})
        try:
            client.execute(cwd=str(ROOT), env=offline_environment(temporary))
        finally:
            if manager.has_kernel:
                manager.shutdown_kernel(now=True)
    for cell in book.cells:
        cell.metadata.pop("execution", None)
        for output in cell.get("outputs", []):
            if output.output_type == "error":
                raise RuntimeError("The executed notebook contains an error")
    nbformat.validate(book)
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    nbformat.write(book, out / NOTEBOOK.name)
    exporter = HTMLExporter(template_name="basic")
    fragment, _ = exporter.from_notebook_node(book)
    for old, new in [(r"\(p-y\)^2", "(p − y)²"), ("$(p-y)^2$", "(p − y)²"),
                     ("$(4+k)/(8+n)$", "(4+k)/(8+n)"), ("$k$", "k"), ("$n$", "n"),
                     ("$y$", "y"), ("$x$", "x"), ("$E_t$", "Eₜ"), ("$b_t$", "bₜ"),
                     ("$h_t$", "hₜ"), ("$t$", "t"), ("$S_t=(x,E_t,b_t,h_t)$", "Sₜ = (x, Eₜ, bₜ, hₜ)")]:
        fragment = fragment.replace(old, new)
    if re.search(r'<(?:script|iframe)\b|\b(?:src|poster)=["\x27](?:https?:)?//', fragment, flags=re.I):
        raise ValueError("Unexpected active content or remote asset in HTML preview")
    prefix = Path(os.path.relpath(ROOT, out)).as_posix()
    fragment = re.sub(r'href="\.\./([^"]+)"', lambda match: f'href="{prefix}/{match[1]}"', fragment)
    html = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>PAIEC · BLE 1.5-A Explained</title><style>' + STYLE +
        '</style></head><body><main><header>PAIEC · Computational research walkthrough</header>' +
        fragment + '</main></body></html>'
    )
    (out / "01_BLE_1_5A_Explained.html").write_text(html)
    count = sum(cell.cell_type == "code" for cell in book.cells)
    images = sum("image/png" in o.get("data", {}) for cell in book.cells for o in cell.get("outputs", []))
    assert images >= 8
    receipt = {"status":"PASS", "cells":len(book.cells), "code_cells_executed":count,
               "png_outputs":images, "execution_errors":0, "paid_requests":0,
               "kernel_transport":"fresh local IPC", "elapsed_seconds":round(time.monotonic()-started,2)}
    (out / "NOTEBOOK_EXECUTION.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
