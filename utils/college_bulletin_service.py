from database.connection import get_connection


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
    conn = get_connection()
    if not conn:
        raise Exception("Connexion base impossible")

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            WITH subject_scores AS (
                SELECT
                    cs.subject_id,
                    cs.coefficient,
                    COALESCE(MAX(CASE WHEN g.grade_type = 'classe' THEN g.value END), 0) AS classe_note,
                    COALESCE(MAX(CASE WHEN g.grade_type = 'compo' THEN g.value END), 0) AS compo_note
                FROM class_subjects cs
                WHERE cs.class_id = %s
                GROUP BY cs.subject_id, cs.coefficient
            ),
            subject_averages AS (
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
                    GROUP BY cs.subject_id, cs.coefficient
                ) ss
            )
            SELECT
                COALESCE(SUM(note_def) / NULLIF(SUM(coefficient), 0), 0)
            FROM subject_averages
            """,
            (class_id, student_id, term_id, class_id)
        )
        row = cursor.fetchone()
        return float(row[0] or 0)

    finally:
        conn.close()


def get_general_rank(class_id: int, student_id: int, term_id: int) -> tuple[int, int]:
    conn = get_connection()
    if not conn:
        raise Exception("Connexion base impossible")

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
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
                  AND st.is_active = TRUE
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
            """,
            (term_id, class_id)
        )

        rows = cursor.fetchall()
        effectif = len(rows)
        rank = 0

        for index, row in enumerate(rows, start=1):
            if row[0] == student_id:
                rank = index
                break

        return rank, effectif

    finally:
        conn.close()


def get_subject_rank(class_id: int, subject_id: int, student_id: int, term_id: int) -> int:
    conn = get_connection()
    if not conn:
        raise Exception("Connexion base impossible")

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
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
              AND st.is_active = TRUE
            GROUP BY e.student_id
            ORDER BY subject_avg DESC, e.student_id
            """,
            (subject_id, term_id, class_id)
        )

        rows = cursor.fetchall()

        for index, row in enumerate(rows, start=1):
            if row[0] == student_id:
                return index

        return 0

    finally:
        conn.close()


def get_class_statistics(class_id: int, term_id: int) -> dict:
    conn = get_connection()
    if not conn:
        raise Exception("Connexion base impossible")

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
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
                  AND st.is_active = TRUE
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
            ,
            (term_id, class_id)
        )

        row = cursor.fetchone()

        return {
            "highest_average": round(float(row[0] or 0), 2),
            "lowest_average": round(float(row[1] or 0), 2),
            "class_average": round(float(row[2] or 0), 2),
        }

    finally:
        conn.close()


def get_annual_average(class_id: int, student_id: int) -> float:
    term_avgs = [
        get_term_average_for_student(class_id, student_id, 1),
        get_term_average_for_student(class_id, student_id, 2),
        get_term_average_for_student(class_id, student_id, 3),
    ]
    existing = [avg for avg in term_avgs if avg > 0]

    if not existing:
        return 0.0

    return round(sum(existing) / len(existing), 2)


def get_annual_rank(class_id: int, student_id: int) -> int:
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
              AND s.is_active = TRUE
            ORDER BY s.id
            """,
            (class_id,)
        )
        student_ids = [row[0] for row in cursor.fetchall()]

        annuals = []
        for sid in student_ids:
            annual_avg = get_annual_average(class_id, sid)
            annuals.append((sid, annual_avg))

        annuals.sort(key=lambda x: (-x[1], x[0]))

        for index, (sid, _) in enumerate(annuals, start=1):
            if sid == student_id:
                return index

        return 0

    finally:
        conn.close()


def get_bulletin_number(class_id: int, student_id: int) -> int:
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
              AND s.is_active = TRUE
            ORDER BY s.last_name, s.first_name
            """,
            (class_id,)
        )
        rows = cursor.fetchall()

        for index, row in enumerate(rows, start=1):
            if row[0] == student_id:
                return index

        return 0

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
            school_year_name,
            titular_name,
        ) = student_row

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
              AND s.is_active = TRUE
            """,
            (class_id,)
        )
        effectif, boys, girls = cursor.fetchone()

        # Détail des matières
        cursor.execute(
            """
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
            GROUP BY
                cs.subject_id,
                sb.name,
                cs.coefficient,
                ta.teacher_id,
                tr.last_name,
                tr.first_name
            ORDER BY sb.name
            """,
            (student_id, term_id, term_id, class_id)
        )

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
            rang = get_subject_rank(class_id, subject_id, student_id, term_id)
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
        general_rank, _ = get_general_rank(class_id, student_id, term_id)

        avg_trim_1 = get_term_average_for_student(class_id, student_id, 1)
        avg_trim_2 = get_term_average_for_student(class_id, student_id, 2)
        avg_trim_3 = get_term_average_for_student(class_id, student_id, 3)
        annual_average = get_annual_average(class_id, student_id)
        annual_rank = get_annual_rank(class_id, student_id)

        class_stats = get_class_statistics(class_id, term_id)
        annual_observation = get_general_observation(annual_average)
        bulletin_number = get_bulletin_number(class_id, student_id)

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
            "avg_trim_1": round(avg_trim_1, 2),
            "avg_trim_2": round(avg_trim_2, 2),
            "avg_trim_3": round(avg_trim_3, 2),
            "annual_average": annual_average,
            "annual_rank": annual_rank,
            "class_highest_average": class_stats["highest_average"],
            "class_lowest_average": class_stats["lowest_average"],
            "class_general_average": class_stats["class_average"],
            "annual_observation": annual_observation,
        }

    finally:
        conn.close()