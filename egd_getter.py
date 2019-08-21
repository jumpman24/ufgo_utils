import argparse
import requests
import re
from bs4 import BeautifulSoup

TOURNAMENT_CARD_URL = "http://www.europeangodatabase.eu/EGD/Tournament_Card.php"
PLAYER_CARD_URL = "http://www.europeangodatabase.eu/EGD/Player_Card.php"
GAME_PATTERN = re.compile(r'(\d+[-=+](/[hbw]\d?)?)|(0[-=+])')
SKIP_PATTERN = re.compile(r'0[-=+]')

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def get_wallist(tournament_pin: str) -> str:
    response = requests.get(TOURNAMENT_CARD_URL, params={'key': tournament_pin})
    bs = BeautifulSoup(response.text, 'html.parser')
    wallist_simple = bs.find(id='wallist_simple').text

    if wallist_simple:
        return wallist_simple

    raise Exception(f"Tournament [{tournament_pin}] was not found in EGD")


def get_player_rating(tournament_pin: str, player_pin: str) -> int:
    response = requests.get(PLAYER_CARD_URL, params={'key': player_pin})
    bs = BeautifulSoup(response.text, 'html.parser')

    tournament_row = bs.find('a', text=tournament_pin)

    if tournament_row:
        rating = tournament_row.find_parent('tr').find(text=re.compile(r"\d+ --> \d+"))
        return rating.split()[0]

    raise Exception(f"Player [{player_pin}] rating for tournament [{tournament_pin}] was not found in EGD")


def parse_row(row: str) -> dict:
    row_array = row.split()

    if len(row_array) < 6:
        raise Exception("Unsupported tournament data format")

    row_data = {
        'pin': row_array[-1][1:] if row_array[-1].startswith('|') else None,
        'place': row_array[0],
        'last_name': row_array[1],
        'first_name': row_array[2],
        'rating': '',
        'rank': row_array[3],
        'country': row_array[4],
        'club': row_array[5],
        'games': [],
    }

    for item in row_array[6:]:
        if GAME_PATTERN.match(item):
            row_data['games'].append(item)

    return row_data


def parse_wallist(wallist: str) -> list:
    parsed = []

    for row in wallist.split('\n'):
        if not row.strip() or row.startswith(';'):
            continue
        print(row)

        parsed.append(parse_row(row.strip()))

    return parsed


def wallist_rank_to_rating(tournament_pin: str, parsed_wallist: list):
    with_ratings = []
    for row in parsed_wallist:
        row_copy = row.copy()

        if row_copy['pin']:
            row_copy['rating'] = get_player_rating(tournament_pin, row_copy['pin'])
            rating_output = bcolors.OKBLUE + row_copy['rating'] + bcolors.ENDC

        elif all([game == "0=" for game in row_copy['games']]):
            rating_output = bcolors.WARNING + 'no PIN, no games' + bcolors.ENDC

        else:
            rating_output = bcolors.FAIL + 'no PIN' + bcolors.ENDC

        print(f"{row_copy['last_name']} {row_copy['first_name']}: {rating_output}")

        with_ratings.append(row_copy)

    return with_ratings


if __name__ == '__main__':
    pin = input("Please, enter tournament PIN: ")

    wallist = get_wallist(pin)
    print("Wallist found. Processing ratings...")

    parsed_wallist = parse_wallist(wallist)

    print(f"Wallist found. Total: {len(parsed_wallist)}. Fetching ratings...")
    wallist_with_ratings = wallist_rank_to_rating(pin, parsed_wallist)

    place_length = 0
    name_length = 0
    game_length = 0
    rounds = 100
    for row in wallist_with_ratings:
        place_length = max(place_length, len(row['place']))
        name_length = max(name_length, len(row['last_name'] + ' ' + row['first_name']))

        if len(row['games']) < rounds:
            print(f"Round number changed to {len(row['games'])}")
            rounds = len(row['games'])

        game_length = max(game_length, max([len(game) for game in row['games']]))

    data = ''
    for player in wallist_with_ratings:
        data += f"{player['place']:{place_length}s} "
        data += f"{player['last_name'] + ' ' + player['first_name']:{name_length}s} "
        data += f"{player['rank']:3s} "
        data += f"{player['rating']:4s} "

        for game in player['games'][-rounds:]:
            data += f"{game:{game_length}s} "

        data += '\n'

    with open(f"{pin}.txt", mode='w+') as f:
        f.write(data)

    print(data)
