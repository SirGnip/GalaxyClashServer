import os
import random
import string
import time
from dataclasses import dataclass
from enum import Enum
from flask import Flask, request
from threading import Barrier


app = Flask(__name__)

MAP_WIDTH = 20
MAP_HEIGHT = 20
NEUTRAL = 'Neutral'


class State(Enum):
  LOBBY = 1
  PLAYING = 2
  END = 3

@dataclass
class Planet:
  name: str
  x: int
  y: int
  ships: int
  owner: str
  production: int

  @staticmethod
  def random_planet(name):
    x = random.randint(0, MAP_WIDTH - 1)
    y = random.randint(0, MAP_HEIGHT - 1)
    ships = random.randint(1, 10)
    production = random.randint(1, 5)
    return Planet(name, x, y, ships, NEUTRAL, production)


class Planets:
  def __init__(self):
    self.planets = []

  def collides(self, planet):
    '''Tests if given planet collides with any existing planet'''
    existing = [(p.x, p.y) for p in self.planets]
    return (planet.x, planet.y) in existing
  
  def generate_map(self, planet_count, players):
    assert planet_count >= len(players)
    
    # generate map
    for planet_name in string.ascii_uppercase[:planet_count]:
      while True:
        planet = Planet.random_planet(planet_name)
        if not self.collides(planet):
          break
      self.planets.append(planet)

    # assign players
    for player, planet in zip(players, self.planets):
      planet.owner = player
      planet.production = 10
      

class Game:
  def __init__(self):
    self.state = State.LOBBY
    self.clients = []
    self.planets = Planets()
    self.fleets = []
    self.barrier = Barrier(999)

  def init_new_turns(self):
    print(f'Created barrier for {len(self.clients)} clients')
    self.barrier = Barrier(len(self.clients))
    
  def add_client(self, client):
    if client not in self.clients:
      self.clients.append(client)

  def start_play(self):
    if self.state == State.LOBBY:
      self.state = State.PLAYING

      planet_count = 10
      print(f'Generating map with {planet_count} planets')
      self.planets.generate_map(planet_count, self.clients)
      
      self.init_new_turns()
    else:
      print('WARN: someone tried to start game that was already started')
    
  def as_json(self):
    return {
        "state": self.state.name,
        "clients": self.clients,
        "planets": self.planets.planets,
        "fleets": self.fleets
    }


game = Game()


@app.route('/')
def index():
  owner = os.getenv('REPL_OWNER')
  slug = os.getenv('REPL_SLUG')
  return f'Hello from Flask!<br>{owner} {slug}'


@app.route('/debug_blocking/<label>/<int:delay>')
def debug_blocking(label, delay):
  msg = f'label: START {label} {delay}'
  print(msg)
  time.sleep(delay)
  print(f'label: END   {label} {delay}')
  return msg


@app.route('/login/<name>')
def login(name):
  print('args', type(request.args), request.args)
  game.add_client(name)
  return game.as_json()


@app.route('/start')
def start():
  game.start_play()
  return game.as_json()


@app.route('/turn')
def turn():
  print('Turn:', request.args)
  plyr = request.args['player']
  turn = request.args['turn']
  game.fleets.append(f'{plyr} => {turn}')
 
  if turn == 'end':
    game.state = State.END
    
  print(f'Entering wait for {plyr}')
  wait_resp = game.barrier.wait()
  print(f'Wait resp {plyr}={wait_resp}')
  print(f'Passed wait for {plyr}')
  if wait_resp == 0:  # have only one thread trigger the barrier reset
    game.init_new_turns()
  
  return game.as_json()


app.run(host='0.0.0.0', port=8080, debug=True)
# https://GalaxyClashServer.sirgnip.repl.co/
