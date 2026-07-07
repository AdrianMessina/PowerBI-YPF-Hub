"""Storage Mode Analyzer + DirectQuery Validator + Query Folding Detector.

Analiza modelos Power BI para:
- Distribución de tablas por storage mode (Import/DirectQuery/Dual)
- Errores críticos DirectQuery (columnas calculadas, funciones no soportadas)
- Anti-patterns de query folding en M code
"""

import re


# Funciones DAX no soportadas en DirectQuery (subset habitual de errores).
# Fuente: docs Microsoft + patrones observados en producción.
DAX_UNSUPPORTED_IN_DIRECTQUERY = {
    "FORMAT", "TEXT",
    "MEDIAN", "MEDIANX",
    "PERCENTILE", "PERCENTILE.EXC", "PERCENTILE.INC",
    "PERCENTILEX.EXC", "PERCENTILEX.INC",
    "GEOMEAN", "GEOMEANX",
    "PRODUCT", "PRODUCTX",
    "PATH", "PATHITEM", "PATHITEMREVERSE", "PATHLENGTH", "PATHCONTAINS",
    "OPENINGBALANCEMONTH", "OPENINGBALANCEQUARTER", "OPENINGBALANCEYEAR",
    "CLOSINGBALANCEMONTH", "CLOSINGBALANCEQUARTER", "CLOSINGBALANCEYEAR",
    "TOTALYTD", "TOTALMTD", "TOTALQTD",
    "SAMEPERIODLASTYEAR", "PARALLELPERIOD",
}

# M functions/expressions que rompen query folding en fuentes SQL.
M_FOLDING_BREAKERS = [
    (r"Text\.Upper\s*\(", "Text.Upper — no folder"),
    (r"Text\.Lower\s*\(", "Text.Lower — no folder"),
    (r"Text\.Proper\s*\(", "Text.Proper — no folder"),
    (r"Text\.Reverse\s*\(", "Text.Reverse — no folder"),
    (r"Text\.Length\s*\(", "Text.Length — puede no folder"),
    (r"Text\.PadStart\s*\(", "Text.PadStart — no folder"),
    (r"Text\.PadEnd\s*\(", "Text.PadEnd — no folder"),
    (r"Table\.AddIndexColumn\s*\(", "Table.AddIndexColumn — no folder"),
    (r"Table\.Buffer\s*\(", "Table.Buffer — corta el folding"),
    (r"List\.Buffer\s*\(", "List.Buffer — corta el folding"),
    (r"Table\.FuzzyGroup\w*\s*\(", "Table.Fuzzy* — no folder"),
    (r"Table\.NestedJoin\s*\(", "Table.NestedJoin — merges custom no folder"),
]


def analyze_storage(all_tables: list) -> dict:
    """Analiza storage mode y valida DirectQuery.

    Args:
        all_tables: lista de tablas (con partitions[]) del modelo parseado.

    Returns:
        dict con:
        - tables_by_mode: contador por mode
        - storage_mode_type: "import" | "directQuery" | "dual" | "composite"
        - directquery_tables_detail: detalle de tablas DQ
        - directquery_issues: errores/warnings críticos
        - query_folding_warnings: anti-patterns detectados en M
    """
    # Filtrar solo tablas reales del usuario (no auto date, no system)
    user_tables = [
        t for t in all_tables
        if not t.get("isSystemTable", False)
        and t.get("tableType", "user") in ("user", "calculated")
    ]

    counts = {"import": 0, "directQuery": 0, "dual": 0}
    dq_detail = []
    issues = []
    folding_warnings = []

    for t in user_tables:
        mode = t.get("mode", "import")
        tname = t.get("name", "")
        counts[mode] = counts.get(mode, 0) + 1

        if mode in ("directQuery", "dual"):
            # Capturar snippet de source (primera partition M/entityRef)
            src_snippet = ""
            for p in t.get("partitions", []):
                if p.get("kind") in ("m", "entityRef") and p.get("source"):
                    src = p["source"]
                    src_snippet = (src[:200] + "…") if len(src) > 200 else src
                    break

            dq_detail.append({
                "name": tname,
                "mode": mode,
                "source_snippet": src_snippet,
                "n_calculated_columns": sum(
                    1 for c in t.get("columns", [])
                    if c.get("type") == "calculated" or c.get("expression")
                ),
            })

            # ── VALIDATION 1: NO columnas calculadas en DirectQuery ──
            for c in t.get("columns", []):
                if c.get("type") == "calculated" or c.get("expression"):
                    issues.append({
                        "severity": "critical",
                        "table": tname,
                        "column": c.get("name", ""),
                        "issue": "Columna calculada en tabla DirectQuery",
                        "detail": (
                            "Las columnas calculadas se materializan al refresh, "
                            "no en query time. En DirectQuery esto rompe el modelo "
                            "o degrada performance dramáticamente. Mové la lógica "
                            "a Power Query (M) o a una vista SQL en el origen."
                        ),
                    })

            # ── VALIDATION 2: DirectQuery calculated table ──
            if t.get("isCalculatedTable"):
                issues.append({
                    "severity": "critical",
                    "table": tname,
                    "column": "",
                    "issue": "Tabla calculada DAX en DirectQuery",
                    "detail": (
                        "Las tablas calculadas (CALCULATETABLE, GROUPBY, etc.) "
                        "requieren Import mode. Convertí a vista SQL o Import."
                    ),
                })

            # ── VALIDATION 3: Query folding anti-patterns ──
            for p in t.get("partitions", []):
                if p.get("kind") != "m":
                    continue
                src = p.get("source", "")
                for pattern, label in M_FOLDING_BREAKERS:
                    if re.search(pattern, src):
                        folding_warnings.append({
                            "table": tname,
                            "antipattern": label,
                            "snippet": _extract_snippet(src, pattern),
                        })

        # ── VALIDATION 4: funciones DAX no soportadas en DQ (medidas) ──
        if mode in ("directQuery", "dual"):
            for m in t.get("measures", []):
                expr = m.get("expression", "")
                # Match función seguida de ( — case insensitive
                for fn in DAX_UNSUPPORTED_IN_DIRECTQUERY:
                    if re.search(rf"\b{re.escape(fn)}\s*\(", expr, re.IGNORECASE):
                        issues.append({
                            "severity": "warning",
                            "table": tname,
                            "column": m.get("name", ""),
                            "issue": f"Función DAX '{fn}' con soporte limitado en DirectQuery",
                            "detail": (
                                f"'{fn}' puede no soportarse en DirectQuery o "
                                "degradar performance. Verificá si tu source admite "
                                "esta operación al foldear la query."
                            ),
                        })

    # Determinar storage mode type del modelo
    n_import = counts["import"]
    n_dq = counts["directQuery"]
    n_dual = counts["dual"]

    if n_dq == 0 and n_dual == 0:
        storage_type = "import"
    elif n_import == 0 and n_dual == 0:
        storage_type = "directQuery"
    elif n_dual > 0 and (n_import > 0 or n_dq > 0):
        storage_type = "composite"
    elif n_import > 0 and n_dq > 0:
        storage_type = "composite"
    else:
        storage_type = "import"

    return {
        "tables_by_mode": counts,
        "storage_mode_type": storage_type,
        "directquery_tables_detail": dq_detail,
        "directquery_issues": issues,
        "query_folding_warnings": folding_warnings,
    }


def _extract_snippet(text: str, pattern: str, ctx_chars: int = 60) -> str:
    """Extrae un fragmento del M code donde matchea el anti-pattern."""
    m = re.search(pattern, text)
    if not m:
        return ""
    start = max(0, m.start() - ctx_chars)
    end = min(len(text), m.end() + ctx_chars)
    snippet = text[start:end].replace("\n", " ").replace("\t", " ")
    snippet = re.sub(r"\s+", " ", snippet).strip()
    return ("…" if start > 0 else "") + snippet + ("…" if end < len(text) else "")
