"""
Divide los examenes oficiales de Fisica de Selectividad en ejercicios individuales,
categorizados segun una referencia de ejercicios ya organizados

Entrada:  ../Fisica/examenesJuntaAndalucia/*.pdf
Salida:   ejercicios/FISICA/{categoria}/
"""

import os
import re
import sys
from pathlib import Path

import fitz  # PyMuPDF

# ---------------------------------------------------------------------------
# Configuracion
# ---------------------------------------------------------------------------
BASE = Path(__file__).parent
EXAMENES_DIR = BASE.parent / "Fisica" / "examenesJuntaAndalucia"
OUTPUT_DIR = BASE / "ejercicios"

# Referencia de ejercicios categorizados 
REF_DIR = BASE.parent / "RepoPrivado" / "ejercicios"

FISICA_CATS = [
    "campo_gravitatorio", "campo_electrico_magnetico",
    "ondas", "optica_geometrica", "fisica_cuantica_nuclear",
]

# Mapeo bloque oficial -> categorias (para 2025)
CAT_TO_BLOCK = {
    "campo_gravitatorio": "A",
    "campo_electrico_magnetico": "B",
    "ondas": "C",
    "optica_geometrica": "C",
    "fisica_cuantica_nuclear": "D",
}

# ---------------------------------------------------------------------------
# Mapeo:  filename_stem -> (year, periodo)
# Obtenido por cross-referencia de texto vs oficiales + eliminacion
# ---------------------------------------------------------------------------
FISICA_FILES = {
    # 2018
    "examenFisica (8)": (2018, "junio"),
    "examenFisica (7)": (2018, "septiembre"),
    "examenFisica (10)": (2018, "reserva1"),
    "examenFisica (9)": (2018, "reserva2"),
    "examenFisica (12)": (2018, "reserva3"),
    "examenFisica (11)": (2018, "reserva4"),
    # 2019
    "examenFisica (31)": (2019, "junio"),
    "examenFisica (29)": (2019, "septiembre"),
    "examenFisica (28)": (2019, "reserva1"),
    "examenFisica (30)": (2019, "reserva2"),
    "examenFisica (32)": (2019, "reserva3"),
    "examenFisica (33)": (2019, "reserva4"),
    # 2020
    "examenFisica (40)": (2020, "junio"),
    "examenFisica (39)": (2020, "septiembre"),
    "examenFisica (38)": (2020, "reserva1"),
    "examenFisica (41)": (2020, "reserva2"),
    "examenFisica (42)": (2020, "reserva3"),
    "examenFisica (43)": (2020, "reserva4"),
    # 2021
    "examenFisica (48)": (2021, "junio"),
    "examenFisica (27)": (2021, "julio"),
    "examenFisica (25)": (2021, "reserva1"),
    "examenFisica (26)": (2021, "reserva2"),
    "examenFisica (46)": (2021, "reserva3"),
    "examenFisica (47)": (2021, "reserva4"),
    # 2022
    "examenFisica (45)": (2022, "junio"),
    "examenFisica (44)": (2022, "julio"),
    "examenFisica (34)": (2022, "reserva1"),
    "examenFisica (35)": (2022, "reserva2"),
    "examenFisica (36)": (2022, "reserva3"),
    "examenFisica (37)": (2022, "reserva4"),
    # 2023
    "examenFisica (5)": (2023, "junio"),
    "examenFisica (6)": (2023, "julio"),
    "examenFisica (1)": (2023, "reserva1"),
    "examenFisica (2)": (2023, "reserva2"),
    "examenFisica (3)": (2023, "reserva3"),
    "examenFisica (4)": (2023, "reserva4"),
    # 2024
    "examenFisica (22)": (2024, "junio"),
    "examenFisica (14)": (2024, "julio"),
    "examenFisica (15)": (2024, "reserva1"),
    "examenFisica (16)": (2024, "reserva2"),
    "examenFisica (13)": (2024, "reserva3"),
    "examenFisica (24)": (2024, "reserva4"),
    # 2025
    "examenFisica (21)": (2025, "junio"),
    "examenFisica (23)": (2025, "julio"),
    "examenFisica (19)": (2025, "reserva1"),
    "examenFisica (17)": (2025, "reserva2"),
    "examenFisica (18)": (2025, "reserva3"),
    "examenFisica (20)": (2025, "reserva4"),
}


# ---------------------------------------------------------------------------
# Construir referencia de categorias desde ejercicios organizados
# ---------------------------------------------------------------------------
def build_category_ref(ref_dir: Path):
    """
    Escanea los ejercicios FISICA de referencia y construye:
    {(year, periodo, exercise_id, opcion) -> category}

    Para 2025, el exercise_id se prefija con la letra del bloque (e.g. "A_a")
    para evitar colisiones entre bloques.
    """
    ref = {}
    asig_dir = ref_dir / "FISICA"
    if not asig_dir.is_dir():
        return ref

    for cat_dir in sorted(os.listdir(asig_dir)):
        cat_path = asig_dir / cat_dir
        if not cat_path.is_dir():
            continue

        for f in os.listdir(cat_path):
            if not f.endswith("_unsolved.pdf"):
                continue
            name = f.replace("_unsolved.pdf", "")

            for c in FISICA_CATS:
                m = re.match(rf"^(\d{{4}})_{re.escape(c)}_(.+)$", name)
                if not m:
                    continue

                year = int(m.group(1))
                rest = m.group(2)

                # Extraer opcion si existe
                opcion = None
                m_op = re.search(r"_opcion([AB])$", rest)
                if m_op:
                    opcion = m_op.group(1)
                    rest = rest[:m_op.start()]

                # Separar periodo y exerciseId
                parts = rest.rsplit("_", 1)
                if len(parts) != 2:
                    break

                periodo = parts[0]
                ex_id = parts[1]

                # Para 2025: prefijo con bloque para evitar colisiones
                if year >= 2025:
                    block = CAT_TO_BLOCK.get(cat_dir, "?")
                    ex_id = f"{block}_{ex_id}"

                key = (year, periodo, ex_id, opcion)
                if key not in ref:
                    ref[key] = cat_dir
                break

    return ref


# ---------------------------------------------------------------------------
# Recoger marcadores de ejercicio de TODAS las paginas
# ---------------------------------------------------------------------------
def find_all_exercise_markers(doc, year):
    """
    Devuelve lista de (exercise_id, page_idx, y_top, opcion) en orden de pagina.

    Formatos por era:
      2018-2019: "OPCION A/B" + "1." ... "4."  (ej_id = "1"-"4", opcion A/B)
      2020:      "1." ... "8."                   (ej_id = "1"-"8")
      2021-2024: "A.1." o "A1."                  (ej_id = "A1"-"D2")
      2025:      "A) CAMPO..." cabecera de bloque (ej_id = "A"-"D")
    """
    all_markers = []

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        blocks = page.get_text("dict")["blocks"]
        current_opcion = None

        for block in blocks:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                text = " ".join(span["text"] for span in line["spans"]).strip()
                y_top = line["bbox"][1]

                if year <= 2019:
                    m_op = re.match(r"^OPCI[ÓO]N\s+([AB])$", text, re.IGNORECASE)
                    if m_op:
                        current_opcion = m_op.group(1).upper()
                        all_markers.append((f"_OPCION_{current_opcion}", page_idx, y_top, None))
                        continue
                    m_ej = re.match(r"^(\d+)\.\s", text)
                    if m_ej and current_opcion:
                        ex_num = int(m_ej.group(1))
                        if 1 <= ex_num <= 4:
                            all_markers.append((str(ex_num), page_idx, y_top, current_opcion))

                elif year == 2020:
                    m_ej = re.match(r"^(\d+)\.\s", text)
                    if m_ej:
                        ex_num = int(m_ej.group(1))
                        if 1 <= ex_num <= 8:
                            all_markers.append((str(ex_num), page_idx, y_top, None))

                elif year <= 2024:
                    # Detectar cabeceras de bloque como limite de seccion
                    m_block = re.match(r"^([A-D])\)\s", text)
                    if m_block:
                        all_markers.append((f"_BLOCK_{m_block.group(1).upper()}", page_idx, y_top, None))
                        continue
                    # Soporta "A.1." (2021), "A1." (2024), "D.1 ." y "A2 ."
                    m_ej = re.match(r"^([A-D])\.?\s*(\d)\s*\.\s", text)
                    if m_ej:
                        ex_id = (m_ej.group(1) + m_ej.group(2)).upper()
                        all_markers.append((ex_id, page_idx, y_top, None))

                else:  # 2025
                    # Cabeceras de bloque: "A) CAMPO GRAVITATORIO", etc.
                    m_ej = re.match(r"^([A-D])\)\s", text)
                    if m_ej:
                        ex_id = m_ej.group(1).upper()
                        all_markers.append((ex_id, page_idx, y_top, None))

    return all_markers


# ---------------------------------------------------------------------------
# Extraer un ejercicio como PDF individual (pagina unica)
# ---------------------------------------------------------------------------
def extract_exercise(src_doc, page_idx, y_start, y_end, output_path):
    """Recorta la region del ejercicio y la guarda como PDF."""
    page = src_doc[page_idx]
    page_rect = page.rect

    clip = fitz.Rect(page_rect.x0, y_start - 3, page_rect.x1, y_end)

    pad_top = 45
    pad_bottom = 30
    out_doc = fitz.open()
    new_w = clip.width
    new_h = clip.height + pad_top + pad_bottom
    new_page = out_doc.new_page(width=new_w, height=new_h)

    target_rect = fitz.Rect(0, pad_top, new_w, pad_top + clip.height)
    new_page.show_pdf_page(target_rect, src_doc, page_idx, clip=clip)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    out_doc.save(str(output_path))
    out_doc.close()


# ---------------------------------------------------------------------------
# Extraer ejercicio que cruza paginas
# ---------------------------------------------------------------------------
HEADER_SKIP = 110  # saltar cabecera repetida en paginas de continuacion

def extract_exercise_multi_page(src_doc, start_page, y_start, end_page, y_end, output_path):
    """Extrae un ejercicio que ocupa mas de una pagina."""
    pad_top = 45
    pad_bottom = 30

    clips = []
    for pi in range(start_page, end_page + 1):
        page = src_doc[pi]
        if pi == start_page:
            top = y_start - 3
            bottom = page.rect.height
        elif pi == end_page:
            top = HEADER_SKIP
            bottom = y_end
        else:
            top = HEADER_SKIP
            bottom = page.rect.height
        # Validar que el clip tenga altura positiva
        if bottom <= top + 1:
            continue
        clips.append((pi, fitz.Rect(page.rect.x0, top, page.rect.x1, bottom)))

    total_h = sum(c[1].height for c in clips)
    new_w = src_doc[start_page].rect.width
    out_doc = fitz.open()
    new_page = out_doc.new_page(width=new_w, height=total_h + pad_top + pad_bottom)

    y_off = pad_top
    for pi, clip in clips:
        target = fitz.Rect(0, y_off, new_w, y_off + clip.height)
        new_page.show_pdf_page(target, src_doc, pi, clip=clip)
        y_off += clip.height

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    out_doc.save(str(output_path))
    out_doc.close()


# ---------------------------------------------------------------------------
# Procesar un examen oficial
# ---------------------------------------------------------------------------
def process_exam(exam_path, year, periodo, cat_ref, output_dir, stats):
    """Procesa un examen oficial de Fisica y extrae ejercicios categorizados."""
    doc = fitz.open(str(exam_path))

    # Recoger marcadores de todas las paginas
    all_markers = find_all_exercise_markers(doc, year)

    if not all_markers:
        print("  (sin marcadores de ejercicio)")
        doc.close()
        return

    for i, (ex_id, start_page, y_start, opcion) in enumerate(all_markers):
        # Saltar marcadores de limite de seccion
        if ex_id.startswith("_"):
            continue

        # Determinar final del ejercicio
        if i + 1 < len(all_markers):
            next_id, next_page, next_y, _ = all_markers[i + 1]
            if next_id.startswith("_") and next_page != start_page:
                # Limite de seccion en otra pagina: recortar en el final de la actual
                end_page = start_page
                y_end = doc[start_page].rect.height
            else:
                end_page = next_page
                y_end = next_y - 3
        else:
            end_page = start_page
            y_end = doc[start_page].rect.height

        # Buscar categoria en la referencia
        if year >= 2025:
            # Buscar con bloque + sub-ejercicio
            category = None
            for sub_id in ["a", "b1", "b2"]:
                key = (year, periodo, f"{ex_id}_{sub_id}", None)
                category = cat_ref.get(key)
                if category:
                    break
        else:
            key_with_op = (year, periodo, ex_id, opcion)
            key_no_op = (year, periodo, ex_id, None)
            category = cat_ref.get(key_with_op) or cat_ref.get(key_no_op)

        if not category:
            print(f"  WARN: Sin categoria para {year}/{periodo} ej={ex_id} op={opcion}")
            stats["skipped"] += 1
            continue

        # Nombre del archivo de salida
        opcion_suffix = f"_opcion{opcion}" if opcion else ""
        filename = f"{year}_{category}_{periodo}_{ex_id}{opcion_suffix}_unsolved.pdf"
        out_path = output_dir / "FISICA" / category / filename

        if out_path.exists():
            os.remove(str(out_path))
            stats["replaced"] += 1

        if start_page == end_page:
            extract_exercise(doc, start_page, y_start, y_end, out_path)
        else:
            extract_exercise_multi_page(doc, start_page, y_start, end_page, y_end, out_path)

        stats["extracted"] += 1
        print(f"  {filename}")

    doc.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=== Dividir examenes oficiales de FISICA ===\n")

    # 1. Construir referencia de categorias
    if not REF_DIR.is_dir():
        print(f"No se encuentra la carpeta de referencia: {REF_DIR}")
        print("Se necesita RepoPrivado/ejercicios/FISICA/ para las categorias.")
        sys.exit(1)

    print("Cargando referencia de categorias...")
    cat_ref = build_category_ref(REF_DIR)
    print(f"  FISICA: {len(cat_ref)} ejercicios de referencia\n")

    # 2. Procesar examenes oficiales
    if not EXAMENES_DIR.is_dir():
        print(f"No se encuentra: {EXAMENES_DIR}")
        sys.exit(1)

    stats = {"extracted": 0, "skipped": 0, "replaced": 0}

    for pdf_file in sorted(EXAMENES_DIR.glob("*.pdf")):
        stem = pdf_file.stem

        if stem not in FISICA_FILES:
            continue

        year, periodo = FISICA_FILES[stem]
        print(f"\n{pdf_file.name} -> {year}/{periodo}")

        process_exam(pdf_file, year, periodo, cat_ref, OUTPUT_DIR, stats)

    print(f"\n=== Resumen FISICA ===")
    print(f"Ejercicios extraidos: {stats['extracted']}")
    print(f"Reemplazados: {stats['replaced']}")
    print(f"Sin categoria (saltados): {stats['skipped']}")


if __name__ == "__main__":
    main()
