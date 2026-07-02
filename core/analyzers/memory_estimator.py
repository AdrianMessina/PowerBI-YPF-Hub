"""Memory estimator for Power BI semantic models.

Estimates memory consumption per table/column based on data types,
cardinality heuristics, and model structure. Inspired by tools like
DAX Studio VertiPaq Analyzer and KornAlexander's PBI Fixer Memory Analyzer.

NOTE: Without direct model access, this is a heuristic estimation based on
the model metadata (column types, table count, relationship count).
For exact numbers, use DAX Studio or Fabric's VertiPaq Analyzer.
"""

from dataclasses import dataclass, field


# Estimated bytes per value by data type (VertiPaq compressed averages)
BYTES_PER_VALUE = {
    "string": 24,       # Average for short-medium strings (hash + dictionary)
    "int64": 8,
    "double": 8,
    "decimal": 16,
    "datetime": 8,
    "boolean": 1,
    "binary": 64,       # Very variable, conservative estimate
}

# Overhead per column (dictionary, segment metadata, etc.)
COLUMN_OVERHEAD_BYTES = 4096  # ~4KB per column baseline

# Overhead per relationship (both sides)
RELATIONSHIP_OVERHEAD_BYTES = 2048

# Overhead per table (metadata, internal structures)
TABLE_OVERHEAD_BYTES = 8192


@dataclass
class ColumnMemoryEstimate:
    table: str
    column: str
    data_type: str
    estimated_rows: int = 0
    estimated_bytes: int = 0
    estimated_mb: float = 0.0
    is_key: bool = False
    is_calculated: bool = False
    notes: str = ""


@dataclass
class TableMemoryEstimate:
    name: str
    estimated_rows: int = 0
    column_count: int = 0
    estimated_bytes: int = 0
    estimated_mb: float = 0.0
    columns: list = field(default_factory=list)
    is_calculated: bool = False
    notes: str = ""


@dataclass
class MemoryEstimation:
    total_estimated_mb: float = 0.0
    tables: list = field(default_factory=list)
    top_columns: list = field(default_factory=list)
    recommendations: list = field(default_factory=list)
    model_size_mb: float = 0.0
    compression_ratio: float = 0.0


class MemoryEstimator:
    """Estimate memory consumption of a Power BI semantic model."""

    # Heuristic: estimate rows per table based on model size
    # Average model: ~1M rows per 10MB of model size
    ROWS_PER_MB = 100_000

    def __init__(self, result):
        """Initialize with an AnalysisResult."""
        self.result = result

    def estimate(self) -> MemoryEstimation:
        """Run the memory estimation."""
        estimation = MemoryEstimation(model_size_mb=self.result.model_size_mb)

        model = self.result._raw_model_data
        model_data = model.get("model", model)
        all_tables = model_data.get("tables", [])

        # Filtrar tablas automáticas (Auto Date/Time) y del sistema
        # No deben contarse para estimar memoria del modelo "real" del usuario
        tables = [t for t in all_tables if not self._is_system_table(t)]

        if not tables:
            return estimation

        # Estimate total rows based on model size
        total_estimated_rows = max(
            int(self.result.model_size_mb * self.ROWS_PER_MB),
            10_000,  # minimum
        )

        # Distribute rows among tables (fact tables get more)
        table_row_estimates = self._estimate_table_rows(tables, total_estimated_rows)

        total_bytes = 0
        all_columns = []

        for table in tables:
            tname = table.get("name", "")

            columns = table.get("columns", [])
            est_rows = table_row_estimates.get(tname, 1000)
            is_calc_table = bool(table.get("isCalculatedTable"))

            table_est = TableMemoryEstimate(
                name=tname,
                estimated_rows=est_rows,
                column_count=len(columns),
                is_calculated=is_calc_table,
            )

            table_bytes = TABLE_OVERHEAD_BYTES

            for col in columns:
                cname = col.get("name", "")
                dtype = col.get("dataType", "string").lower()
                is_calc = bool(col.get("expression"))
                is_key = bool(col.get("isKey"))

                bytes_per_val = BYTES_PER_VALUE.get(dtype, 16)
                col_bytes = (bytes_per_val * est_rows) + COLUMN_OVERHEAD_BYTES

                # String columns with high cardinality use more memory
                if dtype == "string" and is_key:
                    col_bytes = int(col_bytes * 1.5)

                # Calculated columns take memory too
                if is_calc:
                    col_bytes = int(col_bytes * 0.8)  # Slightly less (no source data)

                col_est = ColumnMemoryEstimate(
                    table=tname,
                    column=cname,
                    data_type=dtype,
                    estimated_rows=est_rows,
                    estimated_bytes=col_bytes,
                    estimated_mb=round(col_bytes / (1024 * 1024), 2),
                    is_key=is_key,
                    is_calculated=is_calc,
                )

                table_est.columns.append(col_est)
                all_columns.append(col_est)
                table_bytes += col_bytes

            # Add relationship overhead
            rel_count = sum(
                1 for r in self.result.relationships_detail
                if r.from_table == tname or r.to_table == tname
            )
            table_bytes += rel_count * RELATIONSHIP_OVERHEAD_BYTES

            table_est.estimated_bytes = table_bytes
            table_est.estimated_mb = round(table_bytes / (1024 * 1024), 2)
            estimation.tables.append(table_est)
            total_bytes += table_bytes

        estimation.total_estimated_mb = round(total_bytes / (1024 * 1024), 1)

        # Top columns by memory
        all_columns.sort(key=lambda c: c.estimated_bytes, reverse=True)
        estimation.top_columns = all_columns[:20]

        # Compression ratio
        if self.result.model_size_mb > 0 and estimation.total_estimated_mb > 0:
            estimation.compression_ratio = round(
                estimation.total_estimated_mb / self.result.model_size_mb, 1
            )

        # Generate recommendations
        estimation.recommendations = self._generate_recommendations(estimation)

        # Sort tables by memory (descending)
        estimation.tables.sort(key=lambda t: t.estimated_bytes, reverse=True)

        return estimation

    @staticmethod
    def _is_system_table(t: dict) -> bool:
        """Detecta tablas auto-generadas por Power BI (no del usuario)."""
        if t.get("isSystemTable", False):
            return True
        if t.get("tableType", "") in ("auto_datetime_local", "auto_datetime_template", "system_hidden"):
            return True
        tname = t.get("name", "")
        return tname.startswith("LocalDateTable_") or tname.startswith("DateTableTemplate_")

    def _estimate_table_rows(self, tables: list, total_rows: int) -> dict:
        """Distribute estimated rows among tables.

        Heuristic: tables with more columns and relationships (fact tables)
        typically have more rows.

        Asume que `tables` ya viene filtrada (sin auto Date/Time / system).
        """
        scores = {}
        for table in tables:
            tname = table.get("name", "")
            # Safety check por si acaso entran auto-tables
            if self._is_system_table(table):
                continue

            col_count = len(table.get("columns", []))
            measure_count = len(table.get("measures", []))
            is_calc = bool(table.get("isCalculatedTable"))

            # Fact tables usually have fewer columns, more rows
            # Dim tables have more columns, fewer rows
            rel_as_from = sum(
                1 for r in self.result.relationships_detail if r.from_table == tname
            )
            rel_as_to = sum(
                1 for r in self.result.relationships_detail if r.to_table == tname
            )

            # Higher score = more rows
            score = 1.0
            if rel_as_from > rel_as_to:
                score *= 3.0  # Likely fact table (many FKs)
            elif col_count > 15:
                score *= 0.5  # Likely dim table (many attributes)
            if is_calc:
                score *= 0.3  # Calculated tables usually small
            if measure_count > 0 and col_count <= 2:
                score *= 0.1  # Measure-only table

            scores[tname] = score

        total_score = sum(scores.values()) or 1
        return {
            tname: max(int(total_rows * (score / total_score)), 100)
            for tname, score in scores.items()
        }

    def _generate_recommendations(self, estimation: MemoryEstimation) -> list:
        """Generate memory optimization recommendations."""
        recs = []

        # Large tables
        for t in estimation.tables:
            if t.estimated_mb > 50:
                recs.append(
                    f"Tabla '{t.name}' consume ~{t.estimated_mb:.1f} MB estimados. "
                    f"Considere reducir columnas o particiones incrementales."
                )

        # String columns consuming a lot
        for c in estimation.top_columns[:10]:
            if c.data_type == "string" and c.estimated_mb > 5:
                recs.append(
                    f"Columna string '{c.table}'.'{c.column}' consume ~{c.estimated_mb:.1f} MB. "
                    f"Considere truncar, hashear o mover a una dim table."
                )

        # Too many columns
        for t in estimation.tables:
            if t.column_count > 30:
                recs.append(
                    f"Tabla '{t.name}' tiene {t.column_count} columnas. "
                    f"Considere ocultar o eliminar columnas no necesarias."
                )

        # Calculated tables warning
        calc_tables = [t for t in estimation.tables if t.is_calculated]
        if len(calc_tables) > 3:
            recs.append(
                f"{len(calc_tables)} tablas calculadas detectadas. "
                f"Las tablas calculadas consumen memoria y se recalculan en cada refresh."
            )

        return recs
