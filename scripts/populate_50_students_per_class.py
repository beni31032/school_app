from __future__ import annotations

from datetime import date
from pathlib import Path
import random
import re
import sys
import unicodedata

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.connection import get_connection


random.seed(20260517)
SCHOOL_YEAR_NAME = "2025-2026"
STUDENTS_PER_CLASS = 50

MALE_FIRST_NAMES = [
    "Ablam", "Ablode", "Adama", "Adanlete", "Afiavi", "Ahoefa", "Akim", "Aklesso",
    "Anani", "Atsu", "Ayite", "Benoit", "Blaise", "Boco", "Boris", "Cedric",
    "Cedrico", "Codjo", "Dodzi", "Dossou", "Edem", "Elom", "Emmanuel", "Eric",
    "Eugene", "Eyram", "Fabrice", "Francis", "Frederic", "Gabin", "Gerald", "Gilbert",
    "Guy", "Herve", "Ignace", "Ishmael", "Jacques", "Jean", "Junior", "Kafui",
    "Kekeli", "Kenny", "Kevin", "Kokou", "Komlan", "Komi", "Kossi", "Kouassi",
    "Kouma", "Kpodjo", "Kwadjo", "Lawson", "Luc", "Mawuli", "Mensah", "Messan",
    "Narcisse", "Nicolas", "Noel", "Octave", "Pacome", "Pascal", "Richard", "Sena",
    "Seth", "Seyram", "Sosthene", "Steve", "Sylvain", "Theo", "Thibaut", "Yao",
    "Yawovi", "Yves", "Zinsou", "Zoumana",
]

FEMALE_FIRST_NAMES = [
    "Abla", "Adele", "Adjoa", "Adjowa", "Afi", "Afiwa", "Akissi", "Akouvi",
    "Ami", "Aminata", "Anita", "Arielle", "Assana", "Blandine", "Carine", "Clarisse",
    "Cynthia", "Diane", "Djeneba", "Elisabeth", "Emma", "Estelle", "Eugenie", "Eyram",
    "Fati", "Flore", "Gertrude", "Ghislaine", "Grace", "Helene", "Ines", "Irene",
    "Joelle", "Judith", "Karen", "Kayi", "Khadija", "Larissa", "Linda", "Louise",
    "Mariam", "Merveille", "Micheline", "Murielle", "Noelie", "Patricia", "Priscille", "Rachel",
    "Rita", "Ruth", "Sandrine", "Sarah", "Sonia", "Stella", "Suzanne", "Tatiana",
    "Therese", "Vanessa", "Veronique", "Victoire", "Viviane", "Yasmine", "Yawa", "Zeynab",
]

LAST_NAMES = [
    "Adjei", "Agbe", "Agbodjan", "Agbozo", "Aka", "Akakpo", "Aklesso", "Ali",
    "Amavi", "Amani", "Amouzou", "Anani", "Assi", "Atakora", "Ayi", "Ayite",
    "Badji", "Balo", "Bamba", "Banla", "Biaou", "Boko", "Dado", "Dadzie",
    "Dede", "Degbe", "Diallo", "Dogo", "Dogbe", "Dossa", "Fiogbe", "Folly",
    "Fumey", "Gnama", "Gnassingbe", "Gnawoto", "Gnonlonfoun", "Hounkpe", "Kafui", "Kagni",
    "Komi", "Kossi", "Kouadio", "Kouame", "Kouevi", "Kouma", "Koumado", "Kpassa",
    "Kpodar", "Kponou", "Kuevi", "Laleye", "Lare", "Lawson", "Mensah", "Moumouni",
    "Nare", "Ogou", "Sagna", "Sanvee", "Sodji", "Soglo", "Tano", "Tidjani",
    "Tossou", "Traore", "Wotogbe", "Yovo", "Zinsou",
]

LEVEL_BASE_YEAR = {
    "CP1": 2018,
    "CP2": 2017,
    "CE1": 2016,
    "CE2": 2015,
    "CM1": 2014,
    "CM2": 2013,
    "6ème": 2012,
    "5ème": 2011,
    "4ème": 2010,
    "3ème": 2009,
    "2nde A4": 2008,
    "2nde D": 2008,
    "1ère A4": 2007,
    "1ère D": 2007,
    "Tle A4": 2006,
    "Tle D": 2006,
}

OPTIONAL_BY_CLASS = {
    "1ère A4": ["Allemand", "Espagnol", "Dessin", "Enseignement ménager"],
    "1ère D": ["Allemand", "Espagnol", "Dessin", "Enseignement ménager"],
    "Tle A4": ["Allemand", "Espagnol", "Dessin", "Enseignement ménager"],
    "Tle D": ["Allemand", "Espagnol", "Dessin", "Enseignement ménager"],
}


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Za-z0-9]+", "", ascii_value).upper()


def birth_date_for_level(level: str, index: int) -> date:
    base_year = LEVEL_BASE_YEAR.get(level, 2012)
    month = (index % 12) + 1
    day = ((index * 3) % 27) + 1
    return date(base_year, month, day)


def generate_unique_names(total_needed: int):
    combinations = []
    for first_name in FEMALE_FIRST_NAMES:
        for last_name in LAST_NAMES:
            combinations.append((first_name, last_name, "F"))
    for first_name in MALE_FIRST_NAMES:
        for last_name in LAST_NAMES:
            combinations.append((first_name, last_name, "M"))

    random.shuffle(combinations)
    unique = []
    seen = set()
    for first_name, last_name, gender in combinations:
        key = (first_name.upper(), last_name.upper())
        if key in seen:
            continue
        seen.add(key)
        unique.append((first_name, last_name, gender))
        if len(unique) >= total_needed:
            break

    if len(unique) < total_needed:
        raise RuntimeError("Pas assez de combinaisons de noms pour générer tous les élèves.")
    return unique


def main() -> int:
    conn = get_connection()
    if not conn:
        print("Connexion base impossible.")
        return 1

    try:
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM students")
        if int(cur.fetchone()[0]) > 0:
            print("Insertion stoppée: la table students n'est pas vide.")
            conn.rollback()
            return 1

        cur.execute("SELECT COUNT(*) FROM enrollments")
        if int(cur.fetchone()[0]) > 0:
            print("Insertion stoppée: la table enrollments n'est pas vide.")
            conn.rollback()
            return 1

        cur.execute("SELECT id FROM school_years WHERE name = %s LIMIT 1", (SCHOOL_YEAR_NAME,))
        row = cur.fetchone()
        if not row:
            print(f"Année scolaire introuvable: {SCHOOL_YEAR_NAME}")
            conn.rollback()
            return 1
        school_year_id = int(row[0])

        cur.execute(
            """
            SELECT c.id, c.name, c.level, c.establishment_id
            FROM classes c
            ORDER BY c.name
            """
        )
        classes = cur.fetchall()
        total_students_needed = len(classes) * STUDENTS_PER_CLASS
        generated_names = generate_unique_names(total_students_needed)
        name_index = 0

        optional_subject_ids = {}
        for class_name, subject_names in OPTIONAL_BY_CLASS.items():
            optional_subject_ids[class_name] = []
            for subject_name in subject_names:
                cur.execute(
                    """
                    SELECT cs.id
                    FROM class_subjects cs
                    JOIN classes c ON c.id = cs.class_id
                    JOIN subjects s ON s.id = cs.subject_id
                    WHERE c.name = %s
                      AND s.name = %s
                      AND COALESCE(cs.subject_type, 'OBLIGATOIRE') = 'FACULTATIVE'
                    LIMIT 1
                    """,
                    (class_name, subject_name),
                )
                result = cur.fetchone()
                if result:
                    optional_subject_ids[class_name].append((subject_name, int(result[0])))

        inserted_students = 0
        inserted_options = 0

        for class_id, class_name, level, establishment_id in classes:
            class_code = slugify(class_name)[:8]
            for idx in range(1, STUDENTS_PER_CLASS + 1):
                first_name, last_name, gender = generated_names[name_index]
                name_index += 1
                matricule = f"E{establishment_id}-{class_code}-{idx:03d}"
                birth_date = birth_date_for_level(level, idx)

                cur.execute(
                    """
                    INSERT INTO students (
                        matricule, first_name, last_name, birth_date, gender, photo_path, establishment_id, is_active
                    )
                    VALUES (%s, %s, %s, %s, %s, NULL, %s, TRUE)
                    RETURNING id
                    """,
                    (matricule, first_name, last_name, birth_date, gender, establishment_id),
                )
                student_id = int(cur.fetchone()[0])
                inserted_students += 1

                cur.execute(
                    """
                    INSERT INTO enrollments (student_id, class_id, school_year_id)
                    VALUES (%s, %s, %s)
                    """,
                    (student_id, class_id, school_year_id),
                )

                # Pour les classes de première/terminale, on affecte une option facultative
                # pour que les modules notes/bulletins puissent être testés tout de suite.
                if class_name in optional_subject_ids and optional_subject_ids[class_name]:
                    subject_name, class_subject_id = random.choice(optional_subject_ids[class_name])
                    cur.execute(
                        """
                        INSERT INTO student_optional_subjects (student_id, class_subject_id, school_year_id, created_at)
                        VALUES (%s, %s, %s, NOW())
                        """,
                        (student_id, class_subject_id, school_year_id),
                    )
                    inserted_options += 1

            print(f"{class_name}: {STUDENTS_PER_CLASS} élèves insérés")

        conn.commit()
        print("")
        print(f"Total élèves insérés: {inserted_students}")
        print(f"Choix d'options créés: {inserted_options}")
        print("Garantie: aucun élève n'a le même nom complet.")
        return 0

    except Exception as exc:
        conn.rollback()
        print(f"Insertion impossible: {exc}")
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
