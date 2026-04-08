#!/usr/bin/env python3
"""
Smoke test du module Collège.

Ce script vérifie:
1) récupération des données bulletin collège
2) génération d'un PDF collège
3) comportement "suppression de note" (cellule vide -> suppression en base)

Le script restaure l'état initial des notes testées à la fin.
"""

from __future__ import annotations

import os
import sys
from typing import Dict, Optional, Tuple

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.connection import get_connection
from utils.college_bulletin_service import get_college_bulletin_data


GradeSnapshot = Dict[str, Optional[Tuple[float, Optional[float], Optional[int]]]]


def pick_test_context() -> Tuple[int, int, int, int]:
    conn = get_connection()
    if not conn:
        raise RuntimeError("Connexion base impossible")

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                e.class_id,
                e.student_id,
                t.id AS term_id,
                cs.subject_id
            FROM enrollments e
            JOIN students st ON st.id = e.student_id
            JOIN classes c ON c.id = e.class_id
            JOIN cycles cy ON cy.id = c.cycle_id
            JOIN terms t ON t.school_year_id = e.school_year_id
            JOIN class_subjects cs ON cs.class_id = e.class_id
            WHERE cy.name = 'Collège'
              AND st.is_active = TRUE
            ORDER BY t.id DESC, e.class_id, e.student_id
            LIMIT 1
            """
        )
        row = cursor.fetchone()
        if not row:
            raise RuntimeError("Aucune donnée Collège exploitable trouvée en base.")
        return int(row[0]), int(row[1]), int(row[2]), int(row[3])
    finally:
        conn.close()


def get_fallback_user_id() -> Optional[int]:
    conn = get_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users ORDER BY id LIMIT 1")
        row = cursor.fetchone()
        return int(row[0]) if row else None
    except Exception:
        return None
    finally:
        conn.close()


def backup_grade_pair(student_id: int, subject_id: int, term_id: int) -> GradeSnapshot:
    conn = get_connection()
    if not conn:
        raise RuntimeError("Connexion base impossible")

    snapshots: GradeSnapshot = {"classe": None, "compo": None}
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT grade_type, value, max_score, created_by
            FROM grades
            WHERE student_id = %s
              AND subject_id = %s
              AND term_id = %s
              AND grade_type IN ('classe', 'compo')
            """,
            (student_id, subject_id, term_id),
        )
        for grade_type, value, max_score, created_by in cursor.fetchall():
            snapshots[str(grade_type)] = (
                float(value),
                float(max_score) if max_score is not None else None,
                int(created_by) if created_by is not None else None,
            )
        return snapshots
    finally:
        conn.close()


def upsert_grade(
    student_id: int,
    subject_id: int,
    term_id: int,
    grade_type: str,
    value: float,
    user_id: Optional[int],
) -> None:
    conn = get_connection()
    if not conn:
        raise RuntimeError("Connexion base impossible")
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO grades (
                student_id,
                subject_id,
                term_id,
                grade_type,
                value,
                max_score,
                created_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (student_id, subject_id, term_id, grade_type)
            DO UPDATE SET
                value = EXCLUDED.value,
                max_score = EXCLUDED.max_score,
                created_by = EXCLUDED.created_by
            """,
            (student_id, subject_id, term_id, grade_type, value, 20, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_grade(student_id: int, subject_id: int, term_id: int, grade_type: str) -> None:
    conn = get_connection()
    if not conn:
        raise RuntimeError("Connexion base impossible")
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            DELETE FROM grades
            WHERE student_id = %s
              AND subject_id = %s
              AND term_id = %s
              AND grade_type = %s
            """,
            (student_id, subject_id, term_id, grade_type),
        )
        conn.commit()
    finally:
        conn.close()


def count_grade_pair(student_id: int, subject_id: int, term_id: int) -> int:
    conn = get_connection()
    if not conn:
        raise RuntimeError("Connexion base impossible")
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM grades
            WHERE student_id = %s
              AND subject_id = %s
              AND term_id = %s
              AND grade_type IN ('classe', 'compo')
            """,
            (student_id, subject_id, term_id),
        )
        return int(cursor.fetchone()[0] or 0)
    finally:
        conn.close()


def restore_grades(
    student_id: int,
    subject_id: int,
    term_id: int,
    snapshots: GradeSnapshot,
) -> None:
    for grade_type in ("classe", "compo"):
        snap = snapshots.get(grade_type)
        if snap is None:
            delete_grade(student_id, subject_id, term_id, grade_type)
        else:
            value, _max_score, created_by = snap
            upsert_grade(student_id, subject_id, term_id, grade_type, value, created_by)


def main() -> int:
    print("=== Smoke test module Collège ===")

    class_id, student_id, term_id, subject_id = pick_test_context()
    print(
        f"[Contexte] class_id={class_id} student_id={student_id} "
        f"term_id={term_id} subject_id={subject_id}"
    )

    snapshots = backup_grade_pair(student_id, subject_id, term_id)
    fallback_user_id = get_fallback_user_id()

    try:
        print("[Étape 1] Injection notes test...")
        upsert_grade(student_id, subject_id, term_id, "classe", 12.0, fallback_user_id)
        upsert_grade(student_id, subject_id, term_id, "compo", 14.0, fallback_user_id)

        print("[Étape 2] Vérification données bulletin service...")
        data = get_college_bulletin_data(student_id, term_id)
        subject = next(
            (s for s in data["subjects"] if int(s["subject_id"]) == subject_id),
            None,
        )
        if subject is None:
            raise RuntimeError("Matière de test absente des données bulletin.")
        if round(float(subject["classe_note"]), 2) != 12.00:
            raise RuntimeError(
                f"Note classe inattendue: {subject['classe_note']} (attendu 12.0)"
            )
        if round(float(subject["compo_note"]), 2) != 14.00:
            raise RuntimeError(
                f"Note compo inattendue: {subject['compo_note']} (attendu 14.0)"
            )
        print("[OK] Service bulletin collège cohérent.")

        print("[Étape 3] Génération PDF collège...")
        try:
            from utils.college_bulletin_generator import generate_college_bulletin

            pdf_path = generate_college_bulletin(student_id, term_id)
            if not os.path.exists(pdf_path):
                raise RuntimeError(f"PDF non généré: {pdf_path}")
            print(f"[OK] PDF généré: {pdf_path}")
        except ModuleNotFoundError as mod_err:
            if "reportlab" in str(mod_err):
                print("[WARN] reportlab non installé: étape PDF sautée.")
            else:
                raise

        print("[Étape 4] Simulation suppression des notes...")
        delete_grade(student_id, subject_id, term_id, "classe")
        delete_grade(student_id, subject_id, term_id, "compo")
        remaining = count_grade_pair(student_id, subject_id, term_id)
        if remaining != 0:
            raise RuntimeError(
                f"Suppression incomplète: {remaining} note(s) restante(s) au lieu de 0."
            )
        print("[OK] Suppression des notes validée.")

        print("=== Résultat: SUCCESS ===")
        return 0
    finally:
        print("[Cleanup] Restauration des notes initiales...")
        restore_grades(student_id, subject_id, term_id, snapshots)
        print("[Cleanup] Terminé.")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"=== Résultat: FAIL ===\n{exc}")
        raise SystemExit(1)
