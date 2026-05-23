from database.connection import get_connection

_CLASS_LEVEL_CACHE: dict[int, str] = {}
_TERM_SCHOOL_YEAR_CACHE: dict[int, int] = {}
_OPTIONAL_SUBJECT_CACHE: dict[tuple[int, int], bool] = {}
_TERM_AVG_CACHE: dict[tuple[int, int, int], float] = {}
_GENERAL_RANKINGS_CACHE: dict[tuple[int, int, int], tuple[dict[int, int], int]] = {}
_SUBJECT_RANKINGS_CACHE: dict[tuple[int, int, int, int], dict[int, int]] = {}
_CLASS_STATS_CACHE: dict[tuple[int, int, int], dict] = {}
_SCHOOL_YEAR_TERMS_CACHE: dict[int, list[int]] = {}
_ANNUAL_AVG_MAP_CACHE: dict[tuple[int, int], dict[int, float]] = {}
_ANNUAL_RANKINGS_CACHE: dict[tuple[int, int], dict[int, int]] = {}
_BULLETIN_NUMBER_CACHE: dict[tuple[int, int], dict[int, int]] = {}


def clear_college_bulletin_caches() -> None:
    _CLASS_LEVEL_CACHE.clear()
    _TERM_SCHOOL_YEAR_CACHE.clear()
    _OPTIONAL_SUBJECT_CACHE.clear()
    _TERM_AVG_CACHE.clear()
    _GENERAL_RANKINGS_CACHE.clear()
    _SUBJECT_RANKINGS_CACHE.clear()
    _CLASS_STATS_CACHE.clear()
    _SCHOOL_YEAR_TERMS_CACHE.clear()
    _ANNUAL_AVG_MAP_CACHE.clear()
    _ANNUAL_RANKINGS_CACHE.clear()
    _BULLETIN_NUMBER_CACHE.clear()


def _is_student_based_optional_level(level_name: str) -> bool:
    normalized = (level_name or "").strip().lower()
    aliases = ("3eme", "3ème", "seconde", "2nde", "premiere", "première", "1ere", "1ère", "terminale", "tle")
    return any(alias in normalized for alias in aliases)


def _get_class_level(class_id: int) -> str:
    if class_id in _CLASS_LEVEL_CACHE:
        return _CLASS_LEVEL_CACHE[class_id]
    conn = get_connection()
    if not conn:
        raise Exception("Connexion base impossible")
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COALESCE(level, '') FROM classes WHERE id = %s", (class_id,))
        row = cursor.fetchone()
        level = row[0] if row else ""
        _CLASS_LEVEL_CACHE[class_id] = level
        return level
    finally:
        conn.close()


def _is_student_based_optional_class(class_id: int) -> bool:
    return _is_student_based_optional_level(_get_class_level(class_id))


def _get_term_school_year_id(term_id: int) -> int:
    if term_id in _TERM_SCHOOL_YEAR_CACHE:
        return _TERM_SCHOOL_YEAR_CACHE[term_id]
    conn = get_connection()
    if not conn:
        raise Exception("Connexion base impossible")
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT school_year_id FROM terms WHERE id = %s", (term_id,))
        row = cursor.fetchone()
        if not row:
            raise Exception("Trimestre introuvable.")
        school_year_id = int(row[0])
        _TERM_SCHOOL_YEAR_CACHE[term_id] = school_year_id
        return school_year_id
    finally:
        conn.close()


def _is_optional_subject_for_class(class_id: int, subject_id: int) -> bool:
    cache_key = (class_id, subject_id)
    if cache_key in _OPTIONAL_SUBJECT_CACHE:
        return _OPTIONAL_SUBJECT_CACHE[cache_key]
    conn = get_connection()
    if not conn:
        raise Exception("Connexion base impossible")
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COALESCE(subject_type, 'OBLIGATOIRE')
            FROM class_subjects
            WHERE class_id = %s
              AND subject_id = %s
            LIMIT 1
            """,
            (class_id, subject_id),
        )
        row = cursor.fetchone()
        is_optional = bool(row and row[0] == "FACULTATIVE")
        _OPTIONAL_SUBJECT_CACHE[cache_key] = is_optional
        return is_optional
    finally:
        conn.close()


def get_college_appreciation(avg: float) -> str:
    if avg >= 16:
        return "Très bien"
    if avg >= 14:
        return "Bien"
    if avg >= 12:
        return "Assez bien"
    if avg >= 10:
        return "Passable"
    return "Insuffisant"


def get_general_observation(avg: float) -> str:
    if avg >= 16:
        return "Très bien"
    if avg >= 14:
        return "Bien"
    if avg >= 12:
        return "Assez bien"
    if avg >= 10:
        return "Passable"
    return "Insuffisant"


def get_term_average_for_student(class_id: int, student_id: int, term_id: int) -> float:
    cache_key = (class_id, student_id, term_id)
    if cache_key in _TERM_AVG_CACHE:
        return _TERM_AVG_CACHE[cache_key]
    conn = get_connection()
    if not conn:
        raise Exception("Connexion base impossible")

    try:
        cursor = conn.cursor()
        student_based_optional = _is_student_based_optional_class(class_id)
        school_year_id = _get_term_school_year_id(term_id)
        sql = """
            WITH subject_averages AS (
                SELECT
                    ss.subject_id,
                    ss.coefficient,
                    ((ss.classe_note + ss.compo_note) / 2.0) AS moy_trim,
                    (((ss.classe_note + ss.compo_note) / 2.0) * ss.coefficient) AS note_def
                FROM (
                    SELECT
                        cs.subject_id,
                        cs.coefficient,
                        COALESCE(MAX(CASE WHEN g.grade_type = 'classe' THEN g.value END), 0) AS classe_note,
                        COALESCE(MAX(CASE WHEN g.grade_type = 'compo' THEN g.value END), 0) AS compo_note
                    FROM class_subjects cs
                    LEFT JOIN grades g
                        ON g.subject_id = cs.subject_id
                       AND g.student_id = %s
                       AND g.term_id = %s
                    WHERE cs.class_id = %s
        """
        params = [student_id, term_id, class_id]
        if student_based_optional:
            sql += """
                      AND (
                            COALESCE(cs.subject_type, 'OBLIGATOIRE') <> 'FACULTATIVE'
                            OR EXISTS (
                                SELECT 1
                                FROM student_optional_subjects sos
                                WHERE sos.student_id = %s
                                  AND sos.class_subject_id = cs.id
                                  AND sos.school_year_id = %s
                            )
                      )
            """
            params.extend([student_id, school_year_id])
        sql += """
                    GROUP BY cs.subject_id, cs.coefficient
                ) ss
            )
            SELECT
                COALESCE(SUM(note_def) / NULLIF(SUM(coefficient), 0), 0)
            FROM subject_averages
        """
        cursor.execute(sql, params)
        row = cursor.fetchone()
        average = float(row[0] or 0)
        _TERM_AVG_CACHE[cache_key] = average
        return average

    finally:
        conn.close()


def _get_general_ranking_map(class_id: int, term_id: int, school_year_id: int) -> tuple[dict[int, int], int]:
    cache_key = (class_id, term_id, school_year_id)
    if cache_key in _GENERAL_RANKINGS_CACHE:
        return _GENERAL_RANKINGS_CACHE[cache_key]

    conn = get_connection()
    if not conn:
        raise Exception("Connexion base impossible")

    try:
        cursor = conn.cursor()
        student_based_optional = _is_student_based_optional_class(class_id)
        sql = """
            WITH student_subjects AS (
                SELECT
                    e.student_id,
                    cs.subject_id,
                    cs.coefficient,
                    COALESCE(MAX(CASE WHEN g.grade_type = 'classe' THEN g.value END), 0) AS classe_note,
                    COALESCE(MAX(CASE WHEN g.grade_type = 'compo' THEN g.value END), 0) AS compo_note
                FROM enrollments e
                JOIN students st ON st.id = e.student_id
                JOIN class_subjects cs ON cs.class_id = e.class_id
                LEFT JOIN grades g
                    ON g.student_id = e.student_id
                   AND g.subject_id = cs.subject_id
                   AND g.term_id = %s
                WHERE e.class_id = %s
                  AND e.school_year_id = %s
                  AND st.is_active = TRUE
        """
        params = [term_id, class_id, school_year_id]
        if student_based_optional:
            sql += """
                  AND (
                        COALESCE(cs.subject_type, 'OBLIGATOIRE') <> 'FACULTATIVE'
                        OR EXISTS (
                            SELECT 1
                            FROM student_optional_subjects sos
                            WHERE sos.student_id = e.student_id
                              AND sos.class_subject_id = cs.id
                              AND sos.school_year_id = %s
                        )
                  )
            """
            params.append(school_year_id)
        sql += """
                GROUP BY e.student_id, cs.subject_id, cs.coefficient
            ),
            student_totals AS (
                SELECT
                    student_id,
                    SUM(((classe_note + compo_note) / 2.0) * coefficient) AS total_notes,
                    SUM(coefficient) AS total_coef
                FROM student_subjects
                GROUP BY student_id
            )
            SELECT
                st.student_id,
                ROUND(COALESCE(st.total_notes / NULLIF(st.total_coef, 0), 0), 2) AS general_average
            FROM student_totals st
            ORDER BY general_average DESC, st.student_id
        """
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        ranking_map = {row[0]: index for index, row in enumerate(rows, start=1)}
        result = (ranking_map, len(rows))
        _GENERAL_RANKINGS_CACHE[cache_key] = result
        return result
    finally:
        conn.close()


def get_general_rank(class_id: int, student_id: int, term_id: int, school_year_id: int) -> tuple[int, int]:
    ranking_map, effectif = _get_general_ranking_map(class_id, term_id, school_year_id)
    return ranking_map.get(student_id, 0), effectif


def get_subject_rank(
    class_id: int,
    subject_id: int,
    student_id: int,
    term_id: int,
    school_year_id: int
) -> int:
    cache_key = (class_id, subject_id, term_id, school_year_id)
    if cache_key not in _SUBJECT_RANKINGS_CACHE:
        conn = get_connection()
        if not conn:
            raise Exception("Connexion base impossible")

        try:
            cursor = conn.cursor()
            sql = """
                SELECT
                    e.student_id,
                    ROUND((
                        COALESCE(MAX(CASE WHEN g.grade_type = 'classe' THEN g.value END), 0) +
                        COALESCE(MAX(CASE WHEN g.grade_type = 'compo' THEN g.value END), 0)
                    ) / 2.0, 2) AS subject_avg
                FROM enrollments e
                JOIN students st ON st.id = e.student_id
                LEFT JOIN grades g
                    ON g.student_id = e.student_id
                   AND g.subject_id = %s
                   AND g.term_id = %s
                WHERE e.class_id = %s
                  AND e.school_year_id = %s
                  AND st.is_active = TRUE
            """
            params = [subject_id, term_id, class_id, school_year_id]
            if _is_student_based_optional_class(class_id) and _is_optional_subject_for_class(class_id, subject_id):
                sql += """
                  AND EXISTS (
                        SELECT 1
                        FROM student_optional_subjects sos
                        JOIN class_subjects cs
                          ON cs.id = sos.class_subject_id
                        WHERE sos.student_id = e.student_id
                          AND sos.school_year_id = %s
                          AND cs.class_id = %s
                          AND cs.subject_id = %s
                  )
                """
                params.extend([school_year_id, class_id, subject_id])
            sql += """
                GROUP BY e.student_id
                ORDER BY subject_avg DESC, e.student_id
            """
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            _SUBJECT_RANKINGS_CACHE[cache_key] = {
                row[0]: index for index, row in enumerate(rows, start=1)
            }
        finally:
            conn.close()

    return _SUBJECT_RANKINGS_CACHE[cache_key].get(student_id, 0)

def get_class_statistics(class_id: int, term_id: int, school_year_id: int) -> dict:
    cache_key = (class_id, term_id, school_year_id)
    if cache_key in _CLASS_STATS_CACHE:
        return _CLASS_STATS_CACHE[cache_key]
    conn = get_connection()
    if not conn:
        raise Exception("Connexion base impossible")

    try:
        cursor = conn.cursor()
        student_based_optional = _is_student_based_optional_class(class_id)
        sql = """
            WITH student_subjects AS (
                SELECT
                    e.student_id,
                    cs.subject_id,
                    cs.coefficient,
                    COALESCE(MAX(CASE WHEN g.grade_type = 'classe' THEN g.value END), 0) AS classe_note,
                    COALESCE(MAX(CASE WHEN g.grade_type = 'compo' THEN g.value END), 0) AS compo_note
                FROM enrollments e
                JOIN students st ON st.id = e.student_id
                JOIN class_subjects cs ON cs.class_id = e.class_id
                LEFT JOIN grades g
                    ON g.student_id = e.student_id
                   AND g.subject_id = cs.subject_id
                   AND g.term_id = %s
                WHERE e.class_id = %s
                  AND e.school_year_id = %s
                  AND st.is_active = TRUE
        """
        params = [term_id, class_id, school_year_id]
        if student_based_optional:
            sql += """
                  AND (
                        COALESCE(cs.subject_type, 'OBLIGATOIRE') <> 'FACULTATIVE'
                        OR EXISTS (
                            SELECT 1
                            FROM student_optional_subjects sos
                            WHERE sos.student_id = e.student_id
                              AND sos.class_subject_id = cs.id
                              AND sos.school_year_id = %s
                        )
                  )
            """
            params.append(school_year_id)
        sql += """
                GROUP BY e.student_id, cs.subject_id, cs.coefficient
            ),
            student_averages AS (
                SELECT
                    student_id,
                    ROUND(
                        SUM(((classe_note + compo_note) / 2.0) * coefficient) /
                        NULLIF(SUM(coefficient), 0),
                        2
                    ) AS avg_general
                FROM student_subjects
                GROUP BY student_id
            )
            SELECT
                COALESCE(MAX(avg_general), 0),
                COALESCE(MIN(avg_general), 0),
                COALESCE(AVG(avg_general), 0)
            FROM student_averages
        """
        cursor.execute(sql, params)

        row = cursor.fetchone()

        stats = {
            "highest_average": round(float(row[0] or 0), 2),
            "lowest_average": round(float(row[1] or 0), 2),
            "class_average": round(float(row[2] or 0), 2),
        }
        _CLASS_STATS_CACHE[cache_key] = stats
        return stats

    finally:
        conn.close()


def get_school_year_term_ids(school_year_id: int) -> list[int]:
    if school_year_id in _SCHOOL_YEAR_TERMS_CACHE:
        return _SCHOOL_YEAR_TERMS_CACHE[school_year_id]
    conn = get_connection()
    if not conn:
        raise Exception("Connexion base impossible")

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id
            FROM terms
            WHERE school_year_id = %s
            ORDER BY id
            """,
            (school_year_id,)
        )
        term_ids = [row[0] for row in cursor.fetchall()]
        _SCHOOL_YEAR_TERMS_CACHE[school_year_id] = term_ids
        return term_ids
    finally:
        conn.close()


def _get_annual_average_map(class_id: int, school_year_id: int) -> dict[int, float]:
    cache_key = (class_id, school_year_id)
    if cache_key in _ANNUAL_AVG_MAP_CACHE:
        return _ANNUAL_AVG_MAP_CACHE[cache_key]

    conn = get_connection()
    if not conn:
        raise Exception("Connexion base impossible")

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT e.student_id
            FROM enrollments e
            JOIN students s ON s.id = e.student_id
            WHERE e.class_id = %s
              AND e.school_year_id = %s
              AND s.is_active = TRUE
            ORDER BY s.id
            """,
            (class_id, school_year_id),
        )
        student_ids = [row[0] for row in cursor.fetchall()]
    finally:
        conn.close()

    term_ids = get_school_year_term_ids(school_year_id)
    averages: dict[int, float] = {}
    for sid in student_ids:
        term_avgs = [get_term_average_for_student(class_id, sid, tid) for tid in term_ids]
        existing = [avg for avg in term_avgs if avg > 0]
        averages[sid] = round(sum(existing) / len(existing), 2) if existing else 0.0

    _ANNUAL_AVG_MAP_CACHE[cache_key] = averages
    return averages


def get_annual_average(class_id: int, student_id: int, school_year_id: int) -> float:
    return _get_annual_average_map(class_id, school_year_id).get(student_id, 0.0)


def get_annual_rank(class_id: int, student_id: int, school_year_id: int) -> int:
    cache_key = (class_id, school_year_id)
    if cache_key not in _ANNUAL_RANKINGS_CACHE:
        averages = _get_annual_average_map(class_id, school_year_id)
        ranked = sorted(averages.items(), key=lambda item: (-item[1], item[0]))
        _ANNUAL_RANKINGS_CACHE[cache_key] = {
            sid: index for index, (sid, _avg) in enumerate(ranked, start=1)
        }
    return _ANNUAL_RANKINGS_CACHE[cache_key].get(student_id, 0)


def get_bulletin_number(class_id: int, student_id: int, school_year_id: int) -> int:
    cache_key = (class_id, school_year_id)
    if cache_key in _BULLETIN_NUMBER_CACHE:
        return _BULLETIN_NUMBER_CACHE[cache_key].get(student_id, 0)
    conn = get_connection()
    if not conn:
        raise Exception("Connexion base impossible")

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT s.id
            FROM students s
            JOIN enrollments e ON e.student_id = s.id
            WHERE e.class_id = %s
              AND e.school_year_id = %s
              AND s.is_active = TRUE
            ORDER BY s.last_name, s.first_name
            """,
            (class_id, school_year_id)
        )
        rows = cursor.fetchall()
        number_map = {row[0]: index for index, row in enumerate(rows, start=1)}
        _BULLETIN_NUMBER_CACHE[cache_key] = number_map
        return number_map.get(student_id, 0)

    finally:
        conn.close()


def get_college_bulletin_data(student_id: int, term_id: int) -> dict:
    conn = get_connection()
    if not conn:
        raise Exception("Connexion base impossible")

    try:
        cursor = conn.cursor()

        # Infos élève + classe + titulaire + année + trimestre
        cursor.execute(
            """
            SELECT
                s.id,
                s.matricule,
                s.first_name,
                s.last_name,
                s.gender,
                c.id AS class_id,
                c.name AS class_name,
                t.name AS term_name,
                sy.id AS school_year_id,
                sy.name AS school_year_name,
                COALESCE(tt.last_name || ' ' || tt.first_name, '') AS titular_name
            FROM students s
            JOIN enrollments e ON e.student_id = s.id
            JOIN classes c ON c.id = e.class_id
            JOIN terms t ON t.id = %s
            JOIN school_years sy ON sy.id = t.school_year_id
            LEFT JOIN teachers tt ON tt.id = c.titular_teacher_id
            WHERE s.id = %s
              AND e.school_year_id = t.school_year_id
            LIMIT 1
            """,
            (term_id, student_id)
        )

        student_row = cursor.fetchone()
        if not student_row:
            raise Exception("Élève introuvable pour ce trimestre.")

        (
            _student_id,
            matricule,
            first_name,
            last_name,
            gender,
            class_id,
            class_name,
            term_name,
            school_year_id,
            school_year_name,
            titular_name,
        ) = student_row
        student_based_optional = _is_student_based_optional_class(class_id)

        # Effectif + G/F
        cursor.execute(
            """
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE s.gender = 'M') AS boys,
                COUNT(*) FILTER (WHERE s.gender = 'F') AS girls
            FROM students s
            JOIN enrollments e ON e.student_id = s.id
            WHERE e.class_id = %s
              AND e.school_year_id = %s
              AND s.is_active = TRUE
            """,
            (class_id, school_year_id)
        )
        effectif, boys, girls = cursor.fetchone()

        # Détail des matières
        sql = """
            SELECT
                cs.subject_id,
                sb.name AS subject_name,
                cs.coefficient,
                COALESCE(MAX(CASE WHEN g.grade_type = 'classe' THEN g.value END), 0) AS classe_note,
                COALESCE(MAX(CASE WHEN g.grade_type = 'compo' THEN g.value END), 0) AS compo_note,
                COALESCE(ta.teacher_id, 0),
                COALESCE(tr.last_name || ' ' || tr.first_name, '')
            FROM class_subjects cs
            JOIN subjects sb ON sb.id = cs.subject_id
            LEFT JOIN grades g
                ON g.student_id = %s
               AND g.subject_id = cs.subject_id
               AND g.term_id = %s
            LEFT JOIN teacher_assignments ta
                ON ta.class_id = cs.class_id
               AND ta.subject_id = cs.subject_id
               AND ta.school_year_id = (
                    SELECT school_year_id FROM terms WHERE id = %s
               )
            LEFT JOIN teachers tr ON tr.id = ta.teacher_id
            WHERE cs.class_id = %s
        """
        params = [student_id, term_id, term_id, class_id]
        if student_based_optional:
            sql += """
              AND (
                    COALESCE(cs.subject_type, 'OBLIGATOIRE') <> 'FACULTATIVE'
                    OR EXISTS (
                        SELECT 1
                        FROM student_optional_subjects sos
                        WHERE sos.student_id = %s
                          AND sos.class_subject_id = cs.id
                          AND sos.school_year_id = %s
                    )
              )
            """
            params.extend([student_id, school_year_id])
        sql += """
            GROUP BY
                cs.subject_id,
                sb.name,
                cs.coefficient,
                ta.teacher_id,
                tr.last_name,
                tr.first_name
            ORDER BY sb.name
        """
        cursor.execute(sql, params)

        subject_rows = cursor.fetchall()

        subjects = []
        total_coef = 0
        total_notes = 0.0

        for row in subject_rows:
            (
                subject_id,
                subject_name,
                coefficient,
                classe_note,
                compo_note,
                _teacher_id,
                teacher_name,
            ) = row

            classe_note = float(classe_note or 0)
            compo_note = float(compo_note or 0)
            coefficient = int(coefficient or 1)

            moy_trim = round((classe_note + compo_note) / 2.0, 2)
            note_def = round(moy_trim * coefficient, 2)
            rang = get_subject_rank(class_id, subject_id, student_id, term_id, school_year_id)
            appreciation = get_college_appreciation(moy_trim)

            subjects.append({
                "subject_id": subject_id,
                "subject_name": subject_name,
                "classe_note": classe_note,
                "compo_note": compo_note,
                "moy_trim": moy_trim,
                "coefficient": coefficient,
                "note_def": note_def,
                "rang": rang,
                "appreciation": appreciation,
                "teacher_name": teacher_name or "-",
            })

            total_coef += coefficient
            total_notes += note_def

        general_average = round(total_notes / total_coef, 2) if total_coef > 0 else 0.0
        general_rank, _ = get_general_rank(class_id, student_id, term_id, school_year_id)

        term_ids = get_school_year_term_ids(school_year_id)
        term_averages = [get_term_average_for_student(class_id, student_id, tid) for tid in term_ids[:3]]
        while len(term_averages) < 3:
            term_averages.append(0.0)

        annual_average = get_annual_average(class_id, student_id, school_year_id)
        annual_rank = get_annual_rank(class_id, student_id, school_year_id)

        class_stats = get_class_statistics(class_id, term_id, school_year_id)
        annual_observation = get_general_observation(annual_average)
        bulletin_number = get_bulletin_number(class_id, student_id, school_year_id)

        return {
            "student_id": student_id,
            "bulletin_number": bulletin_number,
            "matricule": matricule,
            "student_name": f"{last_name} {first_name}",
            "first_name": first_name,
            "last_name": last_name,
            "gender": gender,
            "class_id": class_id,
            "class_name": class_name,
            "term_name": term_name,
            "school_year_name": school_year_name,
            "titular_name": titular_name,
            "effectif": effectif,
            "boys": boys,
            "girls": girls,
            "subjects": subjects,
            "total_coef": total_coef,
            "total_notes": round(total_notes, 2),
            "general_average": general_average,
            "general_rank": general_rank,
            "avg_trim_1": round(term_averages[0], 2),
            "avg_trim_2": round(term_averages[1], 2),
            "avg_trim_3": round(term_averages[2], 2),
            "annual_average": annual_average,
            "annual_rank": annual_rank,
            "class_highest_average": class_stats["highest_average"],
            "class_lowest_average": class_stats["lowest_average"],
            "class_general_average": class_stats["class_average"],
            "annual_observation": annual_observation,
        }

    finally:
        conn.close()
