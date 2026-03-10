"""
Divide los examenes oficiales de Quimica de Selectividad en ejercicios individuales,
categorizados segun una referencia de ejercicios ya organizados.

Entrada:  ../Quimica/sel_quimica/examenesJuntaAndalucia/*.pdf
Salida:   ejercicios/QUIMICA/{categoria}/
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
EXAMENES_DIR = BASE.parent / "Quimica" / "sel_quimica" / "examenesJuntaAndalucia"
OUTPUT_DIR = BASE / "ejercicios"

# Referencia de ejercicios categorizados
REF_DIR = BASE.parent / "RepoPrivado" / "ejercicios"

QUIMICA_CATS = [
    "acido_base", "energia_reacciones", "enlaces_quimicos",
    "equilibrio_precipitacion", "equilibrio_quimico", "estructura_atomo",
    "formulacion_quimica", "quimica_organica", "reacciones_redox",
    "transformacion_quimica",
]

# ---------------------------------------------------------------------------
# Mapeo:  filename_stem -> (year, periodo)
# Solo 2018-2025
# ---------------------------------------------------------------------------
QUIMICA_FILES = {
    # 2018
    "examenQuimica (7)": (2018, "junio"),
    "examenQuimica (12)": (2018, "septiembre"),
    "examenQuimica (10)": (2018, "reserva1"),
    "examenQuimica (9)": (2018, "reserva2"),
    "examenQuimica (8)": (2018, "reserva3"),
    "examenQuimica (11)": (2018, "reserva4"),
    # 2019
    "examenQuimica (33)": (2019, "junio"),
    "examenQuimica (32)": (2019, "septiembre"),
    "examenQuimica (29)": (2019, "reserva1"),
    "examenQuimica (28)": (2019, "reserva2"),
    "examenQuimica (31)": (2019, "reserva3"),
    "examenQuimica (30)": (2019, "reserva4"),
    # 2020
    "examenQuimica (45)": (2020, "junio"),
    "examenQuimica (48)": (2020, "septiembre"),
    "examenQuimica (43)": (2020, "reserva1"),
    "examenQuimica (44)": (2020, "reserva2"),
    "examenQuimica (46)": (2020, "reserva3"),
    "examenQuimica (47)": (2020, "reserva4"),
    # 2021
    "examenQuimica (38)": (2021, "junio"),
    "examenQuimica (27)": (2021, "julio"),
    "examenQuimica (25)": (2021, "reserva1"),
    "examenQuimica (26)": (2021, "reserva2"),
    "examenQuimica (36)": (2021, "reserva3"),
    "examenQuimica (37)": (2021, "reserva4"),
    # 2022
    "examenQuimica (35)": (2022, "junio"),
    "examenQuimica (34)": (2022, "julio"),
    "examenQuimica (39)": (2022, "reserva1"),
    "examenQuimica (40)": (2022, "reserva2"),
    "examenQuimica (41)": (2022, "reserva3"),
    "examenQuimica (42)": (2022, "reserva4"),
    # 2023
    "examenQuimica (5)": (2023, "junio"),
    "examenQuimica (6)": (2023, "julio"),
    "examenQuimica": (2023, "reserva1"),
    "examenQuimica (2)": (2023, "reserva2"),
    "examenQuimica (3)": (2023, "reserva3"),
    "examenQuimica (4)": (2023, "reserva4"),
    # 2024
    "examenQuimica (22)": (2024, "junio"),
    "examenQuimica (24)": (2024, "julio"),
    "examenQuimica (15)": (2024, "reserva1"),
    "examenQuimica (16)": (2024, "reserva2"),
    "examenQuimica (13)": (2024, "reserva3"),
    "examenQuimica (14)": (2024, "reserva4"),
    # 2025
    "examenQuimica (21)": (2025, "junio"),
    "examenQuimica (23)": (2025, "julio"),
    "examenQuimica (17)": (2025, "reserva1"),
    "examenQuimica (19)": (2025, "reserva2"),
    "examenQuimica (18)": (2025, "reserva3"),
    "examenQuimica (20)": (2025, "reserva4"),
}


# ---------------------------------------------------------------------------
# Construir referencia de categorias desde ejercicios organizados
# ---------------------------------------------------------------------------
def build_category_ref(ref_dir: Path):
    """
    Escanea los ejercicios QUIMICA de referencia y construye:
    {(year, periodo, exercise_id, opcion) -> category}
    """
    ref = {}
    asig_dir = ref_dir / "QUIMICA"
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

            for c in QUIMICA_CATS:
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
      2018-2019: "OPCION A/B" + "1.-" ... "6.-"  (ej_id = "1"-"6", opcion A/B)
      2020-2024: "A1."/"A2.", "B1."-"B6.", "C1."-"C4."
      2025:      "1A."/"1B.", "2A."/"2B.", ..., "4A."/"4B.", PREGUNTA 5
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
                    # Detectar "OPCIÓN A" / "OPCIÓN B"
                    m_op = re.match(r"^OPCI[ÓO]N\s+([AB])$", text, re.IGNORECASE)
                    if m_op:
                        current_opcion = m_op.group(1).upper()
                        continue
                    # Detectar "1.- " o "1. " (ejercicios numerados 1-6)
                    m_ej = re.match(r"^(\d+)\.-?\s", text)
                    if m_ej and current_opcion:
                        ex_num = int(m_ej.group(1))
                        if 1 <= ex_num <= 6:
                            all_markers.append((str(ex_num), page_idx, y_top, current_opcion))

                elif year <= 2024:
                    # Soporta "A1.", "B3.", "C1 .", "A2 ." (con espacios)
                    m_ej = re.match(r"^([A-C])\.?\s*(\d)\s*\.\s", text)
                    if m_ej:
                        ex_id = (m_ej.group(1) + m_ej.group(2)).upper()
                        all_markers.append((ex_id, page_idx, y_top, None))

                else:  # 2025
                    # Detectar "1A.", "2B.", etc. (preguntas 1-4 con opcion A/B)
                    m_ej = re.match(r"^(\d+)([AB])\.\s", text)
                    if m_ej:
                        n = int(m_ej.group(1))
                        if 1 <= n <= 4:
                            ex_id = m_ej.group(1) + m_ej.group(2)
                            all_markers.append((ex_id, page_idx, y_top, None))
                    # Detectar "PREGUNTA 5" para la pregunta 5 (sin opcion)
                    m_p5 = re.match(r"^PREGUNTA\s+5\b", text, re.IGNORECASE)
                    if m_p5:
                        all_markers.append(("5", page_idx, y_top, None))

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
HEADER_SKIP = 110

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
    """Procesa un examen oficial de Quimica y extrae ejercicios categorizados."""
    doc = fitz.open(str(exam_path))

    all_markers = find_all_exercise_markers(doc, year)

    if not all_markers:
        print("  (sin marcadores de ejercicio)")
        doc.close()
        return

    for i, (ex_id, start_page, y_start, opcion) in enumerate(all_markers):
        # Determinar final del ejercicio
        if i + 1 < len(all_markers):
            _, next_page, next_y, _ = all_markers[i + 1]
            end_page = next_page
            y_end = next_y - 3
        else:
            end_page = len(doc) - 1
            y_end = doc[end_page].rect.height

        # Buscar categoria en la referencia
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
        out_path = output_dir / "QUIMICA" / category / filename

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
    print("=== Dividir examenes oficiales de QUIMICA ===\n")

    # 1. Construir referencia de categorias
    if not REF_DIR.is_dir():
        print(f"No se encuentra la carpeta de referencia: {REF_DIR}")
        print("Se necesita RepoPrivado/ejercicios/QUIMICA/ para las categorias.")
        sys.exit(1)

    print("Cargando referencia de categorias...")
    cat_ref = build_category_ref(REF_DIR)
    print(f"  QUIMICA: {len(cat_ref)} ejercicios de referencia\n")

    # 2. Procesar examenes oficiales
    if not EXAMENES_DIR.is_dir():
        print(f"No se encuentra: {EXAMENES_DIR}")
        sys.exit(1)

    stats = {"extracted": 0, "skipped": 0, "replaced": 0}

    for pdf_file in sorted(EXAMENES_DIR.glob("*.pdf")):
        stem = pdf_file.stem

        if stem not in QUIMICA_FILES:
            continue

        year, periodo = QUIMICA_FILES[stem]
        print(f"\n{pdf_file.name} -> {year}/{periodo}")

        process_exam(pdf_file, year, periodo, cat_ref, OUTPUT_DIR, stats)

    print(f"\n=== Resumen QUIMICA ===")
    print(f"Ejercicios extraidos: {stats['extracted']}")
    print(f"Reemplazados: {stats['replaced']}")
    print(f"Sin categoria (saltados): {stats['skipped']}")


if __name__ == "__main__":
    main()
