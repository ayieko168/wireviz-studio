from pathlib import Path

from wireviz_studio.export.csv_export import export_csv
from wireviz_studio.export.svg_export import export_svg
from wireviz_studio.gui.export import ExportSelection, ExportWorker

MINIMAL_SVG = """<svg xmlns='http://www.w3.org/2000/svg' width='120' height='80'>
<rect x='0' y='0' width='120' height='80' fill='white'/>
<text x='10' y='40' font-size='14'>WireViz</text>
</svg>"""

SAMPLE_BOM = [
    {"id": 1, "description": "Connector", "qty": 2, "designators": ["X1", "X2"]}
]


def test_export_svg_writes_file(tmp_path):
    output = tmp_path / "diagram.svg"

    export_svg(MINIMAL_SVG, str(output))

    assert output.exists()
    assert "<svg" in output.read_text(encoding="utf-8")


def test_export_csv_writes_header_and_row(tmp_path):
    output = tmp_path / "bom.csv"

    export_csv(SAMPLE_BOM, str(output))

    contents = output.read_text(encoding="utf-8")
    assert "id,description,qty,designators" in contents
    assert "Connector" in contents


def test_export_worker_normalizes_missing_extension():
    assert ExportWorker._normalized_path("out/diagram", "SVG").endswith(".svg")
    assert ExportWorker._normalized_path("out/diagram", "png").endswith(".png")


def test_export_worker_dispatches_to_expected_backend(monkeypatch, tmp_path):
    called = {"name": None, "path": None}

    def fake_export_svg(svg_text, output_path):
        called["name"] = "svg"
        called["path"] = output_path
        Path(output_path).write_text(svg_text, encoding="utf-8")

    monkeypatch.setattr("wireviz_studio.gui.export.export_svg", fake_export_svg)

    selection = ExportSelection(format_name="SVG", output_path=str(tmp_path / "out"), pdf_mode="diagram")
    worker = ExportWorker(selection=selection, svg_data=MINIMAL_SVG, bom_rows=SAMPLE_BOM)
    worker.run()

    assert called["name"] == "svg"
    assert called["path"].endswith(".svg")


def test_export_worker_dispatches_png_backend(monkeypatch, tmp_path):
    called = {"name": None, "path": None}

    def fake_export_png(svg_text, output_path):
        called["name"] = "png"
        called["path"] = output_path
        Path(output_path).write_bytes(b"PNG")

    monkeypatch.setattr("wireviz_studio.gui.export.export_png", fake_export_png)

    selection = ExportSelection(format_name="PNG", output_path=str(tmp_path / "out"), pdf_mode="diagram")
    worker = ExportWorker(selection=selection, svg_data=MINIMAL_SVG, bom_rows=SAMPLE_BOM)
    worker.run()

    assert called["name"] == "png"
    assert called["path"].endswith(".png")


def test_export_worker_dispatches_pdf_backend(monkeypatch, tmp_path):
    called = {"name": None, "path": None, "mode": None}

    def fake_export_pdf(svg_text, rows, output_path, pdf_mode):
        called["name"] = "pdf"
        called["path"] = output_path
        called["mode"] = pdf_mode
        Path(output_path).write_bytes(b"PDF")

    monkeypatch.setattr("wireviz_studio.gui.export.export_pdf", fake_export_pdf)

    selection = ExportSelection(format_name="PDF", output_path=str(tmp_path / "out"), pdf_mode="both")
    worker = ExportWorker(selection=selection, svg_data=MINIMAL_SVG, bom_rows=SAMPLE_BOM)
    worker.run()

    assert called["name"] == "pdf"
    assert called["path"].endswith(".pdf")
    assert called["mode"] == "both"
