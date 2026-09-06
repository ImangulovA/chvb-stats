#!/usr/bin/env python3
"""
Classify tournaments from worldwide_results.json into categories.
"""

import json
import re
from collections import defaultdict
from datetime import datetime


def classify_tournament(name: str) -> str:
    """
    Classify a tournament based on its name.

    Priority order (first match wins):
    1. mirror - (зеркало), (асинхрон), (онлайн), Онлайн:
    2. school - школьный, школьников
    3. student - студенческий, студентов
    4. youth - молодёжный, ювенальский, детский
    5. league - высшая лига, первая лига, вторая лига, этап, отбор
    6. special - language variants, unusual names
    7. main - everything else that's a national championship
    """
    name_lower = name.lower()

    # Skip non-championships
    if "открытый всероссийский синхронный чемпионат" in name_lower:
        return None

    # 1. Mirror/async/online
    mirror_patterns = [
        r'\(зеркало\)',
        r'\(асинхрон',
        r'\(онлайн\)',
        r'^онлайн:',
    ]
    for pattern in mirror_patterns:
        if re.search(pattern, name_lower):
            return 'mirror'

    # 2. School
    school_patterns = [
        r'школьн',
        r'среди школьников',
    ]
    for pattern in school_patterns:
        if re.search(pattern, name_lower):
            return 'school'

    # 3. Student
    student_patterns = [
        r'студенческ',
        r'среди студентов',
    ]
    for pattern in student_patterns:
        if re.search(pattern, name_lower):
            return 'student'

    # 4. Youth
    youth_patterns = [
        r'молодёжн',
        r'молодежн',
        r'ювенальн',
        r'детск',
    ]
    for pattern in youth_patterns:
        if re.search(pattern, name_lower):
            return 'youth'

    # 5. League/stages
    league_patterns = [
        r'высшая лига',
        r'первая лига',
        r'вторая лига',
        r'третья лига',
        r'переходн.+этап',
        r'предварительный этап',
        r'\.\s+отбор',
        r'\d+\s+этап',
        r'этап\s+\d+',
        r'\.\s+\d+\s+этап',
        r'\.\s+этап\s+\d+',
    ]
    for pattern in league_patterns:
        if re.search(pattern, name_lower):
            return 'league'

    # 6. Special - language variants, unusual names
    special_patterns = [
        r'на русском языке',
        r'на румынском языке',
        r'на азербайджанском',
        r'\(на азербайджанском\)',
        r'обрезанн',
        r'без фальстартов',
        r'по заковат',
        r'по zakovat',
        r'по quantum',
    ]
    for pattern in special_patterns:
        if re.search(pattern, name_lower):
            return 'special'

    # 7. Main - everything else
    return 'main'


def main():
    # Read worldwide results
    print("Loading worldwide_results.json...")
    with open('data/worldwide_results.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    classification = {}
    stats = defaultdict(lambda: defaultdict(int))

    print("\nClassifying tournaments...")
    for country_id_str, country_data in data.items():
        country_id = int(country_id_str)
        country_name = country_data['country']['name']

        # Initialize categories
        categories = {
            'main': [],
            'student': [],
            'school': [],
            'youth': [],
            'league': [],
            'mirror': [],
            'special': []
        }

        # Classify each tournament
        for tournament_id_str, tournament_data in country_data.get('tournaments', {}).items():
            tournament_id = int(tournament_id_str)
            tournament_info = tournament_data['info']
            tournament_name = tournament_info['name']

            # Skip tournaments with 0 teams
            results = tournament_data.get('results', [])
            if len(results) == 0:
                continue

            # Classify
            category = classify_tournament(tournament_name)
            if category is None:
                # Skip excluded tournaments
                continue

            # Store tournament with date for sorting
            date_start = tournament_info.get('dateStart', '')
            categories[category].append({
                'id': tournament_id,
                'date': date_start,
                'name': tournament_name
            })

            stats[country_name][category] += 1

        # Sort each category by date and extract IDs
        for category in categories:
            categories[category].sort(key=lambda x: x['date'])
            categories[category] = [t['id'] for t in categories[category]]

        classification[country_id] = {
            'country_name': country_name,
            **categories
        }

    # Save classification
    print("\nSaving classification to data/tournament_classification.json...")
    with open('data/tournament_classification.json', 'w', encoding='utf-8') as f:
        json.dump(classification, f, ensure_ascii=False, indent=2)

    # Print summary table
    print("\n" + "="*80)
    print("TOURNAMENT CLASSIFICATION SUMMARY")
    print("="*80)
    print(f"{'Country':<25} {'Main':>6} {'Student':>7} {'School':>6} {'Youth':>6} {'League':>6} {'Mirror':>6} {'Special':>7} {'Total':>6}")
    print("-"*80)

    total_stats = defaultdict(int)
    for country_name in sorted(stats.keys()):
        country_stats = stats[country_name]
        total = sum(country_stats.values())
        total_stats['total'] += total

        print(f"{country_name:<25} "
              f"{country_stats['main']:>6} "
              f"{country_stats['student']:>7} "
              f"{country_stats['school']:>6} "
              f"{country_stats['youth']:>6} "
              f"{country_stats['league']:>6} "
              f"{country_stats['mirror']:>6} "
              f"{country_stats['special']:>7} "
              f"{total:>6}")

        for category in ['main', 'student', 'school', 'youth', 'league', 'mirror', 'special']:
            total_stats[category] += country_stats[category]

    print("-"*80)
    print(f"{'TOTAL':<25} "
          f"{total_stats['main']:>6} "
          f"{total_stats['student']:>7} "
          f"{total_stats['school']:>6} "
          f"{total_stats['youth']:>6} "
          f"{total_stats['league']:>6} "
          f"{total_stats['mirror']:>6} "
          f"{total_stats['special']:>7} "
          f"{total_stats['total']:>6}")
    print("="*80)

    print("\n✓ Done! Classification saved to data/tournament_classification.json")


if __name__ == '__main__':
    main()
