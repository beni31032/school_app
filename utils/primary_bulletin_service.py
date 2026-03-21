from database.connection import get_connection


def get_primary_observation(average: float) -> str:
    if average >= 9:
        return "Excellent"
    if average >= 8:
        return "Très bien"
    if average >= 7:
        return "Bien"
    if average >= 6:
        return "Assez bien"
    if average >= 5:
        return "Passable"
    return "Insuffisant"


def get_primary_admission(average: float) -> str:
    return "Oui" if average >= 5 else "Non"


def get_student_rank(class_id: int, term_id: int, student_id: int) -> tuple[int, int]:
    conn = get_connection()
    if not conn:
        raise Exception("Connexion base impossible")

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            WITH class_subject_names AS (
                SELECT DISTINCT s.name AS subject_name
                FROM class_subjects cs
                JOIN subjects s ON s.id = cs.subject_id
                WHERE cs.class_id = %s
            ),
            student_totals AS (
                SELECT
                    e.student_id,
                    SUM(
                        COALESCE((
                            SELECT MAX(g.value)
                            FROM grades g
                            JOIN subjects gs ON gs.id = g.subject_id
                            JOIN class_subjects csg
                                ON csg.subject_id = gs.id
                               AND csg.class_id = e.class_id
                            WHERE g.student_id = e.student_id
                              AND g.term_id = %s
                              AND gs.name = csn.subject_name
                        ), 0)
                    ) AS total_points
                FROM enrollments e
                CROSS JOIN class_subject_names csn
                JOIN students s ON s.id = e.student_id
                WHERE e.class_id = %s
                  AND s.is_active = TRUE
                GROUP BY e.student_id
            )
            SELECT
                s.id,
                st.total_points
            FROM student_totals st
            JOIN students s ON s.id = st.student_id
            ORDER BY st.total_points DESC, s.last_name, s.first_name
            """,
            (class_id, term_id, class_id)
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


def get_class_score_extremes(class_id: int, term_id: int) -> tuple[float, float]:
    conn = get_connection()
    if not conn:
        raise Exception("Connexion base impossible")

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            WITH class_subject_names AS (
                SELECT DISTINCT s.name AS subject_name
                FROM class_subjects cs
                JOIN subjects s ON s.id = cs.subject_id
                WHERE cs.class_id = %s
            ),
            student_totals AS (
                SELECT
                    e.student_id,
                    SUM(
                        COALESCE((
                            SELECT MAX(g.value)
                            FROM grades g
                            JOIN subjects gs ON gs.id = g.subject_id
                            JOIN class_subjects csg
                                ON csg.subject_id = gs.id
                               AND csg.class_id = e.class_id
                            WHERE g.student_id = e.student_id
                              AND g.term_id = %s
                              AND gs.name = csn.subject_name
                        ), 0)
                    ) AS total_points
                FROM enrollments e
                CROSS JOIN class_subject_names csn
                JOIN students s ON s.id = e.student_id
                WHERE e.class_id = %s
                  AND s.is_active = TRUE
                GROUP BY e.student_id
            )
            SELECT total_points
            FROM student_totals
            ORDER BY total_points DESC
            """,
            (class_id, term_id, class_id)
        )

        rows = cursor.fetchall()

        if not rows:
            return 0.0, 0.0

        totals = [float(row[0] or 0) for row in rows]
        return max(totals), min(totals)

    finally:
        conn.close()


def get_primary_bulletin_data(student_id: int, term_id: int) -> dict:
    conn = get_connection()
    if not conn:
        raise Exception("Connexion base impossible")

    try:
        cursor = conn.cursor()

        # Infos élève + classe + trimestre + année + titulaire
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
            titular_name
        ) = student_row

        # Une seule ligne par NOM de matière
        cursor.execute(
            """
            WITH class_subject_names AS (
                SELECT DISTINCT s.name AS subject_name
                FROM class_subjects cs
                JOIN subjects s ON s.id = cs.subject_id
                WHERE cs.class_id = %s
            )
            SELECT
                csn.subject_name,
                COALESCE((
                    SELECT MAX(g.value)
                    FROM grades g
                    JOIN subjects gs ON gs.id = g.subject_id
                    JOIN class_subjects csg
                        ON csg.subject_id = gs.id
                       AND csg.class_id = %s
                    WHERE g.student_id = %s
                      AND g.term_id = %s
                      AND gs.name = csn.subject_name
                ), 0) AS score,
                COALESCE((
                    SELECT MAX(g.max_score)
                    FROM grades g
                    JOIN subjects gs ON gs.id = g.subject_id
                    JOIN class_subjects csg
                        ON csg.subject_id = gs.id
                       AND csg.class_id = %s
                    WHERE g.student_id = %s
                      AND g.term_id = %s
                      AND gs.name = csn.subject_name
                ), 10) AS max_score
            FROM class_subject_names csn
            ORDER BY csn.subject_name
            """,
            (class_id, class_id, student_id, term_id, class_id, student_id, term_id)
        )

        grade_rows = cursor.fetchall()

        subjects = []
        total_score = 0.0
        total_max = 0.0

        for idx, row in enumerate(grade_rows, start=1):
            subject_name, score, max_score = row
            score = float(score or 0)
            max_score = float(max_score or 10)

            subjects.append({
                "subject_id": idx,
                "subject_name": subject_name,
                "score": score,
                "max_score": max_score
            })

            total_score += score
            total_max += max_score

        average = 0.0
        if subjects:
            average = total_score / len(subjects)

        rank, effectif = get_student_rank(class_id, term_id, student_id)
        note_max, note_min = get_class_score_extremes(class_id, term_id)

        observation = get_primary_observation(average)
        admitted = get_primary_admission(average)

        return {
            "student_id": student_id,
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
            "subjects": subjects,
            "total_score": round(total_score, 2),
            "total_max": round(total_max, 2),
            "average": round(average, 2),
            "rank": rank,
            "effectif": effectif,
            "note_max": round(note_max, 2),
            "note_min": round(note_min, 2),
            "observation": observation,
            "admitted": admitted,
        }

    finally:
        conn.close()