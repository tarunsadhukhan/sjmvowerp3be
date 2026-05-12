"""
Jute Production - Spinning Report Queries.

Five report views are supported:
  1. /production-eff      Date x Quality x Shift production + efficiency
  2. /mc-date             Machine x Date production + efficiency
  3. /emp-date            Employee x Date production + efficiency
  4. /frame-running       Frame-wise running hours + efficiency
  5. /running-hours-eff   Production efficiency on running-hours basis

Source tables are NOT yet finalized — every query returns an empty result set
(WHERE 1=0) as a placeholder. Fill in the FROM/JOIN/WHERE clauses and column
projections once the spinning transaction schema is confirmed. The response
shape (column names + types) MUST be preserved so the frontend pivots work.

Quality master: spinning_quality_mst (already used in masters/spinningQuality).
Joins should use:  spinning_quality_mst.spinning_qlty_id  /  spinning_qlty_name
(adjust to the real column names when wiring real SQL).

Parameter list across all queries:
  :branch_id   int
  :from_date   'YYYY-MM-DD'
  :to_date     'YYYY-MM-DD'
"""

from sqlalchemy import text


# ---------------------------------------------------------------------------
# 1. Spinning Production and Efficiency (Date x Quality x Shift)
# ---------------------------------------------------------------------------


def get_spinning_production_eff_query():
    """
    One row per (date, quality, spell). Frontend pivots into shift columns:
      Frames per shift, Production per shift + Overall, Eff (overall), and
      Avg/Frame (overall). Per-date Total rows are injected on the frontend.

    Source:
      - daily_doff_tbl                  net weight per (mc, date, spell)
      - daily_doff_frames_winding       maps (date, spell, mc) -> quality_id
                                        (only spg_wdg = 'S' rows)
      - spinning_quality_mst            quality details (speed, tpi, spindles,
                                        std_count) — used to compute target
                                        production (tarprod)
      - spinning_type_mst               quality type prefix for display
      - spell_mst                       shift / spell name

    Target production formula (per machine-spell-quality):
        tarprod = (speed * 480 * no_of_spindles * std_count)
                  / (tpi * 14400 * 2.20246 * 36)

    Projection per (date, quality, spell):
        report_date    string (dd-mm-YYYY)
        quality_id     int
        quality_name   string  (type + quality - speed tpi - spindles)
        spell_id       int
        spell_name     string
        frames         numeric  — machine count for that shift
        production     numeric  — SUM(net_weight)
        tarprod        numeric  — SUM(target production)

    Parameters: :branch_id (currently unused — daily_doff_tbl has no branch
                column in current schema), :from_date, :to_date ('YYYY-MM-DD')
    """
    sql = """
        SELECT
            DATE_FORMAT(g.doff_date, '%d-%m-%Y')               AS report_date,
            g.quality_id                                       AS quality_id,
            g.quality                                          AS quality_name,
            sm.spell_id                                        AS spell_id,
            COALESCE(sm.spell_name, CONCAT('Shift ', g.spell)) AS spell_name,
            SUM(g.mcs)                                         AS frames,
            ROUND(SUM(g.weight), 2)                            AS production,
            ROUND(SUM(g.tarprod), 2)                           AS tarprod
        FROM (
            SELECT
                ddt.mc_id,
                ddt.doff_date,
                ddt.spell,
                ddfw.quality_id,
                CONCAT(
                    stm.spg_type_name, ' ',
                    sqm.spg_quality, '-',
                    sqm.speed, ' ',
                    sqm.tpi, '-',
                    sqm.no_of_spindles
                )                                              AS quality,
                ddt.wt                                         AS weight,
                ddt.mcs                                        AS mcs,
                (
                    (sqm.speed * 480 * sqm.no_of_spindles * sqm.std_count)
                    / (sqm.tpi * 14400 * 2.20246 * 36)
                )                                              AS tarprod
            FROM (
                SELECT
                    mc_id,
                    doff_date,
                    spell,
                    SUM(net_weight) AS wt,
                    1               AS mcs
                FROM daily_doff_tbl
                WHERE doff_date BETWEEN :from_date AND :to_date
                GROUP BY mc_id, doff_date, spell
            ) ddt
            LEFT JOIN daily_doff_frames_winding ddfw
                   ON ddfw.tran_date = ddt.doff_date
                  AND ddfw.spell     = ddt.spell
                  AND ddfw.mc_eb_id  = ddt.mc_id
                  AND ddfw.spg_wdg   = 'S'
            LEFT JOIN spinning_quality_mst sqm
                   ON sqm.spg_quality_mst_id = ddfw.quality_id
            LEFT JOIN spinning_type_mst stm
                   ON stm.spg_type_mst_id = sqm.spg_type_id
            GROUP BY
                ddt.mc_id,
                ddt.doff_date,
                ddt.spell,
                ddfw.quality_id,
                CONCAT(
                    stm.spg_type_name, ' ',
                    sqm.spg_quality, '-',
                    sqm.speed, ' ',
                    sqm.tpi, '-',
                    sqm.no_of_spindles
                )
        ) g
        LEFT JOIN spell_mst sm ON sm.spell_id = g.spell
        GROUP BY g.doff_date, sm.spell_id, sm.spell_name, g.quality_id, g.quality
        ORDER BY g.doff_date, g.quality, sm.spell_id
    """
    return text(sql)


# ---------------------------------------------------------------------------
# 2. Machine-wise Date-wise Production + Efficiency
# ---------------------------------------------------------------------------


def get_spinning_mc_date_query():
    """
    One row per (date, machine), aggregated across qualities and shifts.
    Frontend pivots into date column groups with Production / Eff% / Avg-per-
    Frame sub-columns + an Overall group on the right.

    Same inner subquery as the production-eff report. The outer SELECT drops
    quality from the GROUP BY so each (machine, date) gets a single row.

    Projection per (date, machine):
        report_date    string (dd-mm-YYYY)
        mc_id          int
        mc_name        string
        frames         numeric  — SUM(mcs)
        production     numeric  — SUM(weight)
        tarprod        numeric  — SUM(tarprod)  (used for eff%)

    Parameters: :branch_id (unused — daily_doff_tbl has no branch column),
                :from_date, :to_date ('YYYY-MM-DD')
    """
    sql = """
        SELECT
            DATE_FORMAT(g.doff_date, '%d-%m-%Y')                    AS report_date,
            g.mc_id                                                 AS mc_id,
            COALESCE(mm.machine_name, CONCAT('Machine #', g.mc_id)) AS mc_name,
            SUM(g.mcs)                                              AS frames,
            ROUND(SUM(g.weight), 2)                                 AS production,
            ROUND(SUM(g.tarprod), 2)                                AS tarprod
        FROM (
            SELECT
                ddt.mc_id,
                ddt.doff_date,
                ddt.spell,
                ddfw.quality_id,
                ddt.wt   AS weight,
                ddt.mcs  AS mcs,
                (
                    (sqm.speed * 480 * sqm.no_of_spindles * sqm.std_count)
                    / (sqm.tpi * 14400 * 2.20246 * 36)
                )        AS tarprod
            FROM (
                SELECT
                    mc_id,
                    doff_date,
                    spell,
                    SUM(net_weight) AS wt,
                    1               AS mcs
                FROM daily_doff_tbl
                WHERE doff_date BETWEEN :from_date AND :to_date
                GROUP BY mc_id, doff_date, spell
            ) ddt
            LEFT JOIN daily_doff_frames_winding ddfw
                   ON ddfw.tran_date = ddt.doff_date
                  AND ddfw.spell     = ddt.spell
                  AND ddfw.mc_eb_id  = ddt.mc_id
                  AND ddfw.spg_wdg   = 'S'
            LEFT JOIN spinning_quality_mst sqm
                   ON sqm.spg_quality_mst_id = ddfw.quality_id
            GROUP BY ddt.mc_id, ddt.doff_date, ddt.spell, ddfw.quality_id
        ) g
        LEFT JOIN machine_mst mm ON mm.machine_id = g.mc_id
        GROUP BY g.doff_date, g.mc_id, mm.machine_name
        ORDER BY mm.machine_name, g.doff_date
    """
    return text(sql)


# ---------------------------------------------------------------------------
# 3. Employee-wise Date-wise Production + Efficiency
# ---------------------------------------------------------------------------


def get_spinning_emp_date_query():
    """
    One row per (date, employee). Frontend pivots into date columns with
    Production / Eff sub-columns + Total + Average groups.

    Expected projection:
        report_date    (string, dd-mm-YYYY)
        emp_id         int
        emp_name       string
        production     numeric
        eff            numeric
    """
    sql = """
        SELECT
            DATE_FORMAT(NULL, '%d-%m-%Y') AS report_date,
            CAST(NULL AS UNSIGNED)        AS emp_id,
            CAST(NULL AS CHAR)            AS emp_name,
            0.0                            AS production,
            0.0                            AS eff
        WHERE 1 = 0
    """
    return text(sql)


# ---------------------------------------------------------------------------
# 4. Frame-wise Running Efficiency (aggregated over the range)
# ---------------------------------------------------------------------------


def get_spinning_frame_running_query():
    """
    One row per frame, aggregated over the date range.

    Expected projection:
        frame_id          int
        frame_name        string
        running_hours     numeric  — actual running hours
        total_hours       numeric  — scheduled / available hours
        eff               numeric  — running_hours / total_hours * 100
    """
    sql = """
        SELECT
            CAST(NULL AS UNSIGNED)        AS frame_id,
            CAST(NULL AS CHAR)            AS frame_name,
            0.0                            AS running_hours,
            0.0                            AS total_hours,
            0.0                            AS eff
        WHERE 1 = 0
    """
    return text(sql)


# ---------------------------------------------------------------------------
# 5. Production Efficiency on Running-Hours basis
# ---------------------------------------------------------------------------


def get_spinning_running_hours_eff_query():
    """
    Per (machine, quality) totals over the date range — production divided by
    running hours.

    Expected projection:
        mc_id             int
        mc_name           string
        quality_id        int
        quality_name      string
        production        numeric
        running_hours     numeric
        eff               numeric  — production-per-hour vs standard rate %
    """
    sql = """
        SELECT
            CAST(NULL AS UNSIGNED)        AS mc_id,
            CAST(NULL AS CHAR)            AS mc_name,
            CAST(NULL AS UNSIGNED)        AS quality_id,
            CAST(NULL AS CHAR)            AS quality_name,
            0.0                            AS production,
            0.0                            AS running_hours,
            0.0                            AS eff
        WHERE 1 = 0
    """
    return text(sql)
