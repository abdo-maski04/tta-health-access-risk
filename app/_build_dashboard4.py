path = 'c:/Users/dell/tta-health-access-risk/app/pages/analytics.py'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Trouver le debut et la fin de l'ancienne render_commune_details
start = None
end = None
for i, line in enumerate(lines):
    if line.startswith('def render_commune_details('):
        start = i
    if start is not None and line.startswith('def _population_by_province'):
        end = i
        break

if start is None or end is None:
    print(f'ERREUR: start={start}, end={end}')
else:
    print(f'Ancienne fonction: lignes {start+1} à {end}')
    # Garder les lignes avant start et après end-1
    new_lines = lines[:start] + lines[end:]
    with open(path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print('Ancienne fonction supprime.')