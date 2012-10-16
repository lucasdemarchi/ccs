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
from operator import attrgetter

COLOR_YELLOW = "\033[1;33m"
COLOR_CLEAR = "\033[0m"

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
        self.games = dict()

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


players = []
# Create all players
for row in thead.next_siblings:
    if isinstance(row, NavigableString):
        continue
    for col in row.children:
        if isinstance(col, NavigableString):
            continue

        players.append(Player(get_name(col)))
        break

i = 0
for row in thead.next_siblings:
    if isinstance(row, NavigableString):
        continue

    x = players[i]
    j = -1
    for col in row.children:
        if isinstance(col, NavigableString):
            continue

        # ignore remaining cols, all is set
        if j >= nplayers:
            break;

        # ignore first column (it's player's name) and player vs player
        if j == -1 or j == i:
            j += 1
            continue

        y = players[j]
        x.games[y] = x.games.get(y, tuple()) + get_games(col)
        j += 1

    i += 1

def calculate_scores(players):
    scores = []
    for p in players:
        s = sum(sum(g) for g in p.games.values())
        scores.append(s)

    return scores

def calculate_tie_breaks(players, scores):
    ties = []
    i = 0
    for p in players:
        s = 0
        for y in p.games.keys():
            j = players.index(y)
            s += sum(g * scores[j] for g in p.games[y])
        ties.append(s)

    return ties

def update_players(players):
    nplayers = len(players)
    scores = calculate_scores(players)
    ties = calculate_tie_breaks(players, scores)

    for i in range(0, nplayers):
        players[i].score = scores[i]
        players[i].tie = ties[i]

    players.sort(key=attrgetter('score', 'tie', 'name'), reverse=True)

def pretty_print_games(players, simulations):
    nplayers = len(players)

    # header
    print('%-18s' % '', end='')
    for i in range(1, nplayers + 1):
        print('%-8s' % ''.join([ str(i), '.']), end='')

    print('| %6s |%10s' % ('Score', 'Tie Break'))
    #             players     +  1st column  + score  + ties  + sep
    print('-' * (nplayers * 8 +  18          + 6      + 10    + 5))

    # table
    i = 0
    for p in players:
        #print name
        print("%d. %-15s" % (i + 1, p.name), end='')

        for j in range(0, nplayers):
            if j == i:
                print("%-8s" % " X", end='')
                continue

            y = players[j]
            if y in p.games.keys():
                n = 0
                for s in simulations:
                    if (s[0] == p and s[1] == y) or (s[0] == y and s[1] == p):
                        n += 1

                fixspaces = 0
                n = len(p.games[y]) - n
                l = []
                for g in p.games[y]:
                    if n > 0:
                        s = str(g)
                    else:
                        fixspaces += 1
                        s = '%s%s%s' % (COLOR_YELLOW, str(g), COLOR_CLEAR)
                    n -= 1
                    l.append(s)

                print('%-8s' % ' '.join(l), end='')

                # Sadly '%-8s' screw up when feed up with colors
                if fixspaces > 0:
                    print(' ' * (8 - (2 * len(l) - 1)), end='')
            else:
                print(' ' * 8, end='')

        print('| %6s |%10s' % (p.score, p.tie))
        i += 1

import cmd

class CssInteractive(cmd.Cmd):
    '''Command line processor for interacting with championship state'''

    prompt = "css> "
    undoc_header = ''

    def __init__(self, players):
        cmd.Cmd.__init__(self)
        self.players = players
        self.results = []

        self.update_players()

    def do_state(self, line):
        '''Print current state of the championship'''

        global nplayers

        print("Number of players: %d\n" % nplayers)
        pretty_print_games(self.players, self.results)

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

        print('%s%s%s' % (x.name, rstr, y.name))

    def update_players(self):
        update_players(self.players)

    def do_push(self, line):
        '''Push new simulation'''
        global nplayers

        try:
            i, j, r = self.parse_line(line)
        except AttributeError:
            print('Could not parse result simulation %s\n' % line)
            return

        if i > nplayers or j > nplayers or i == j:
            print('Invalid players in result simulation %s\n' % line)
            return

        # 0-based index
        x = self.players[i - 1]
        y = self.players[j - 1]

        if len(x.games[y]) >= 2:
            print('All games already played in %s x %s' % (x.name, y.name))
            return

        x.games[y] = x.games.get(y, tuple()) + (r,)
        y.games[x] = y.games.get(x, tuple()) + (1 - r,)
        self.update_players()
        self.results.append((x, y, r))

        print('Simulation added: ', end='')
        self.pretty_print_simulation(self.results[-1])
        self.do_state('')

    def do_simulations(self, line):
        '''Print current simulations'''

        for r in self.results:
            self.pretty_print_simulation(r)

    def do_pop(self, line):
        '''Remove last simulation'''
        if not self.results:
            print('No simulation to pop')
            return

        s = self.results.pop()

        x, y, r = s

        x.games[y] = x.games[y][:-1]
        y.games[x] = y.games[x][:-1]
        self.update_players()

        print('Simulation removed: ', end='')
        self.pretty_print_simulation(s)
        self.do_state('')

    def do_EOF(self, line):
        '''Type ^D to exit'''
        return True

CssInteractive(players).cmdloop()
