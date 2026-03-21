from utils.primary_bulletin_service import get_primary_bulletin_data

student_id = 1
term_id = 1

data = get_primary_bulletin_data(student_id, term_id)

print("Élève :", data["student_name"])
print("Classe :", data["class_name"])
print("Trimestre :", data["term_name"])
print("Année scolaire :", data["school_year_name"])
print("Total note :", data["total_score"])
print("Total sur :", data["total_max"])
print("Moyenne :", data["average"])
print("Rang :", f'{data["rank"]}e sur {data["effectif"]}')
print("Observation :", data["observation"])
print("Admis :", data["admitted"])
print("Note max :", data["note_max"])
print("Note min :", data["note_min"])

print("\nDisciplines :")
for item in data["subjects"]:
    print(f'- {item["subject_name"]}: {item["score"]}/{item["max_score"]}')