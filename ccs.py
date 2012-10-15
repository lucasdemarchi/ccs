#!/usr/bin/env python
#
# Chess Championship Scores
#
# Parse the table generated on chess.com and recreate the scores
# Go to http://www.chess.com/tournament/YOUR-TOURNAMENT-HERE and save the
# generated page - pass this file as argv[1]
#

from __future__ import print_function

import argparse
import re
from bs4 import BeautifulSoup
from bs4 import NavigableString


parser = argparse.ArgumentParser(
        description='Generate scores for a chess.com championship')
parser.add_argument('html_file', nargs=1, type=str,
                    help='html file with current state')
args = parser.parse_args()

class Player:
    def __init__(self, name):
        self.name = name
        self.score = 0
        self.tie = 0

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


f = open(args.html_file[0])
soup = BeautifulSoup(f)

table = soup.find('table', 'pairings')
thead = table.thead

nplayers = 0
for c in thead.tr.contents:
    if isinstance(c, NavigableString):
        continue
    nplayers += 1
nplayers -= 3 # first column, score, tie break

# 1 more column to hold player info
games = [[0 for x in range(nplayers + 1)] for x in range(nplayers)]

i = 0
for row in thead.next_siblings:
    if isinstance(row, NavigableString):
        continue

    j = 0
    for col in row.children:
        if isinstance(col, NavigableString):
            continue

        if j == 0:
            games[i][-1] = Player(get_name(col))
        elif j == i + 1:
            games[i][j - 1] = None
        else:
            games[i][j - 1] = get_games(col)

        j += 1
        if j > nplayers:
            break
    i += 1

def calculate_scores(games):
    scores = []
    for r in games:
        s = 0
        for c in r[:-1]:
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
        for c in r[:-1]:
            j += 1
            if c is None:
                continue
            for g in c:
                t += g * scores[j]

        ties.append(t)


    return ties

def update_games(games, scores, ties):
    i = 0
    for r in games:
        r[-1].score = scores[i]
        r[-1].tie = ties[i]
        i += 1

    games.sort(key=lambda x: x[-1].score * nplayers * 10 + x[-1].tie)
    games.reverse()

def pretty_print_games(games):
    # header
    print('%-18s' % '', end='')
    for i in range(1, nplayers + 1):
        print('%-8s' % ''.join([ str(i), '.']), end='')

    print('| %6s |%10s' % ('Score', 'Tie Break'))
    #             players     +  1st column  + score  + ties  + sep
    print('-' * (nplayers * 8 +  18          + 6      + 10    + 5))

    # table
    i = 0
    for r in games:
        #print name
        print("%d. %-15s" % (i + 1, r[-1].name), end='')
        i += 1

        for c in r[:-1]:
            if c is None:
                print("%-8s" % " X", end='')
                continue

            print('%-8s' % ' '.join([str(g) for g in c]), end='')

        print('| %6s |%10s' % (r[-1].score, r[-1].tie))

import cmd

class CssInteractive(cmd.Cmd):
    '''Command line processor for interacting with championship state'''

    prompt = "css> "
    undoc_header = ''

    def __init__(self, games):
        cmd.Cmd.__init__(self)
        self.games = games
        self.results = []

        self.update_games()

    def do_state(self, line):
        '''Print current state of the championship'''

        global nplayers

        print("Number of players: %d\n" % nplayers)
        pretty_print_games(self.games)

    def parse_line(self, line):
        # Parses name1xname2=result
        m = re.match('(?P<x>[1-9]+)x(?P<y>[1-9]+)=(?P<r>[0|1|0\.5])', line)
        return int(m.group('x')), int(m.group('y')), int(m.group('r'))

    def pretty_print_simulation(self, sim):
        x, y, r = sim
        if r == 0:
            rstr = " loses against "
        elif r == 1:
            rstr = " beats "
        else:
            rstr = " ties with "

        print('%s%s%s' % (self.games[x][-1].name, rstr, self.games[y][-1].name))

    def update_games(self):
        scores = calculate_scores(self.games)
        ties = calculate_tie_breaks(self.games, scores)
        update_games(self.games, scores, ties)

    def do_push(self, line):
        '''Push new simulation'''
        global nplayers

        try:
            x, y, r = self.parse_line(line)
        except AttributeError:
            print('Could not parse result simulation %s\n' % line)
            return

        if x > nplayers or y > nplayers or x == y:
            print('Invalid players in result simulation %s\n' % line)
            return

        if len(self.games[x - 1][y]) >= 2:
            print('All games already played in %s x %s' %
                    (self.games[x - 1][0], self.games[y - 1][0]))
            return

        self.results.append((x, y, r))
        self.games[x][y] += r,
        self.games[y][x] += 1 - r,
        self.update_games()

        print('Simulation added: ', end='')
        self.pretty_print_simulation(self.results[-1])
        self.do_state('')

    def do_simulations(self, line):
        '''Print current simulations'''

        for r in self.results:
            print('%dx%d=%d - ' % (r[0], r[1], r[2]), end='')
            self.pretty_print_simulation(r)

    def do_pop(self, line):
        '''Remove last simulation'''
        s = self.results.pop()
        x, y, r = s

        self.games[x][y] = self.games[x][y][:-1]
        self.games[y][x] = self.games[y][x][:-1]
        self.update_games()

        print('Simulation removed: ', end='')
        self.pretty_print_simulation(s)

    def do_EOF(self, line):
        '''Type ^D to exit'''
        return True

CssInteractive(games).cmdloop()
