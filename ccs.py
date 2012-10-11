#!/usr/bin/env python
#
# Chess Championship Scores
#
# Parse the table generated on chess.com and recreate the scores
# Go to http://www.chess.com/tournament/YOUR-TOURNAMENT-HERE and save the
# generated page - pass this file as argv[1]
#


import sys
from bs4 import BeautifulSoup

def get_name(col):
    return col.find_all('a')[1].text.strip()

def get_games(col):
    games = tuple()
    for a in col.find_all('a'):
        s = a.text.strip()
        #  '_' is on going, 'X' the game doesn't exist
        if s == '_' or s == 'X':
            continue

        games += int(s),

    return games


f = open(sys.argv[1])
soup = BeautifulSoup(f)

table = soup.find('table', 'pairings')
thead = table.thead

nplayers = 0
for c in thead.tr.contents:
    if isinstance(c, str):
        continue
    nplayers += 1
nplayers -= 3 # first column, score, tie break

print("Number of players: %d" % nplayers)

# 1 more column to hold the name
games = [[0 for x in range(nplayers + 1)] for x in range(nplayers)]

i = 0
for row in thead.next_siblings:
    if isinstance(row, str):
        continue

    j = 0
    for col in row.children:
        if isinstance(col, str):
            continue

        if j == 0:
            games[i][j] = get_name(col)
        elif j == i + 1:
            games[i][j] = None
        else:
            games[i][j] = get_games(col)

        j += 1
        if j > nplayers:
            break
    i += 1

def calculate_scores(games):
    scores = []
    for r in games:
        s = 0
        for c in r[1:]:
            if c is None:
                continue
            for g in c:
                s += g
        scores.append(s)

    return scores

def calculate_tie_breaks(games, scores):
    ties = []
    i = 0
    for r in games:
        t = 0
        j = -1
        for c in r[1:]:
            j += 1
            if c is None:
                continue
            for g in c:
                t += g * scores[j]

        ties.append(t)


    return ties

def pretty_print_games(games, scores, ties):
    i = 0
    for r in games:
        j = -1
        for c in r:
            j += 1
            #print name
            if j == 0:
                print("%-15s" % games[i][j], end='')
                continue

            if games[i][j] is None:
                print("%-8s" % " X", end='')
                continue

            print('%-8s' % ' '.join([str(g) for g in games[i][j]]), end='')

        print('%10s%10s' % (scores[i], ties[i]))
        i += 1


scores = calculate_scores(games)
ties = calculate_tie_breaks(games, scores)
pretty_print_games(games, scores, ties)
