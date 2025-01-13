import random
import pygame
from math import sqrt

import protocol
from topology import Topology

SOURCE_INDEX = 0
DESTINATION_INDEX = 1

ROUTER_NUMBER = 100
DISTANCE = 0.4
DISTANCE_2 = DISTANCE * DISTANCE
WINDOW_SIZE = 16
PACKAGE = 64
TIMEOUT = 0.2

WIDTH = 1000
HEIGHT = WIDTH

RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREY = (127, 127, 127)
LIGHT_GREY = (32, 32, 32)

FPS = 60

# Вероятность "поломки" и "восстановления"
REMOVAL_PROBABILITY = 0.01
RECOVERY_PROBABILITY = 0.01

class Router:
    def __init__(self, router_id, coord):
        self.router_id = router_id
        self.coord = coord
        self.color = BLACK
        self.is_failed = False

def metrics(coord1, coord2):
    dx = coord1[0] - coord2[0]
    dy = coord1[1] - coord2[1]
    return sqrt(dx * dx + dy * dy)

def to_screen(coord):
    return [(coord[0] + 1) / 2 * WIDTH, (1 - coord[1]) / 2 * HEIGHT]

def is_connected(r1, r2):
    dx = r1.coord[0] - r2.coord[0]
    dy = r1.coord[1] - r2.coord[1]
    return dx * dx + dy * dy < DISTANCE_2

def initialize():
    routers = []
    for i in range(ROUTER_NUMBER):
        coord = [random.uniform(-1, 1), random.uniform(-1, 1)]
        r = Router(i, coord)
        routers.append(r)

    # Источник (0)
    routers[SOURCE_INDEX].color = RED
    # Приёмник (1)
    routers[DESTINATION_INDEX].color = BLUE
    return routers

prev_path = []
stream = None
topology = Topology()

def step(routers):
    global prev_path
    global stream
    global topology

    # С вероятностью REMOVAL_PROBABILITY ломаем один роутер (кроме 0 и 1)
    candidate_ids = [rtr.router_id for rtr in routers
                     if rtr.router_id not in [SOURCE_INDEX, DESTINATION_INDEX]
                     and not rtr.is_failed]
    if candidate_ids:
        if random.random() < REMOVAL_PROBABILITY:
            victim_id = random.choice(candidate_ids)
            for rtr in routers:
                if rtr.router_id == victim_id:
                    rtr.is_failed = True
                    rtr.color = RED   
                    break

    # С вероятностью RECOVERY_PROBABILITY восстанавливаем один из "красных"
    failed_ids = [rtr.router_id for rtr in routers
                  if rtr.router_id not in [SOURCE_INDEX, DESTINATION_INDEX]
                  and rtr.is_failed]
    if failed_ids:
        if random.random() < RECOVERY_PROBABILITY:
            recovered_id = random.choice(failed_ids)
            for rtr in routers:
                if rtr.router_id == recovered_id:
                    rtr.is_failed = False
                    rtr.color = BLACK
                    break

    topology = Topology()
    for rtr in routers:
        topology.add_new_node(rtr.router_id)

    for i in range(len(routers)):
        # Пропускаем, если роутер i сломан
        if routers[i].is_failed:
            continue
        for j in range(i):
            # Пропускаем, если роутер j сломан
            if routers[j].is_failed:
                continue
            # Если оба живые, и дистанция < порога - создаём связь
            if is_connected(routers[i], routers[j]):
                topology.add_new_link(routers[i].router_id, routers[j].router_id)
                topology.add_new_link(routers[j].router_id, routers[i].router_id)

    # 4. Находим кратчайший путь
    paths = topology.get_shortest_ways(SOURCE_INDEX)
    if not paths:
        return [], [], 0.0
    if DESTINATION_INDEX >= len(paths) or not paths[DESTINATION_INDEX]:
        stream = None
        return [], [], 0.0

    path = paths[DESTINATION_INDEX]
    if len(path) == 0:
        stream = None
        return [], path, 0.0

    # Проверяем, не изменился ли путь
    if len(path) == len(prev_path) and all(path[i] == prev_path[i] for i in range(len(path))):
        stream.update()
        stream.send_msg()
    else:
        # Путь новый - создаём новый объект стрима
        prev_path[:] = path
        stream = Streaming()

    # Возвращаем список рёбер для визуализации, путь и прогресс потока
    return _make_connections(routers), path, stream.progress()

def _make_connections(routers):
    conns = []
    for i in range(len(routers)):
        if routers[i].is_failed:
            continue
        for j in range(i):
            if routers[j].is_failed:
                continue
            if is_connected(routers[i], routers[j]):
                conns.append((i, j))
    return conns

class Streaming:
    def __init__(self):
        self.reciever = protocol.Receiver(WINDOW_SIZE)
        self.sender = protocol.Sender(WINDOW_SIZE, PACKAGE, TIMEOUT)

    def progress(self):
        if self.sender.is_done():
            return 1.0
        return self.sender.ans_count / (self.sender.max_number + 1)

    def send_msg(self):
        if self.sender.send_msg_queue.has_msg():
            self.reciever.recieve_msg_queue.send_message(self.sender.send_msg_queue.get_message())
        if self.reciever.send_msg_queue.has_msg():
            self.sender.recieve_msg_queue.send_message(self.reciever.send_msg_queue.get_message())

    def update(self):
        self.sender.update()
        self.reciever.update()

def render(screen, routers, connections, path, rate=0.0):
    screen.fill(WHITE)

    # Отображаем связи
    for connection in connections:
        i, j = connection
        pygame.draw.line(screen, LIGHT_GREY,
                         to_screen(routers[i].coord),
                         to_screen(routers[j].coord))

    if len(path) != 0:
        path_routers = []
        router_id_map = {r.router_id: r for r in routers}
        for rid in path:
            if rid in router_id_map:
                path_routers.append(router_id_map[rid])

        dists = []
        dist = 0.0
        for i in range(len(path_routers) - 1):
            seg = metrics(path_routers[i].coord, path_routers[i+1].coord)
            dists.append(seg)
            dist += seg
        black_dist = dist * rate
        cur_dist = 0.0
        not_filled_color = LIGHT_GREY
        if rate == 0.0:
            not_filled_color = RED

        for i in range(len(path_routers) - 1):
            coordA = path_routers[i].coord
            coordB = path_routers[i+1].coord
            if cur_dist >= black_dist:
                pygame.draw.line(screen, not_filled_color,
                                 to_screen(coordA),
                                 to_screen(coordB), 3)
            elif cur_dist + dists[i] <= black_dist:
                pygame.draw.line(screen, RED,
                                 to_screen(coordA),
                                 to_screen(coordB), 6)
            else:
                alpha1 = (black_dist - cur_dist) / dists[i]
                alpha2 = 1 - alpha1
                coord1 = [alpha2 * coordA[0] + alpha1 * coordB[0],
                          alpha2 * coordA[1] + alpha1 * coordB[1]]
                pygame.draw.line(screen, RED,
                                 to_screen(coordA),
                                 to_screen(coord1), 6)
                pygame.draw.line(screen, not_filled_color,
                                 to_screen(coord1),
                                 to_screen(coordB), 3)
            cur_dist += dists[i]

    for router in routers:
        pygame.draw.circle(screen, router.color, to_screen(router.coord), 3)

    source_router = next((r for r in routers if r.router_id == SOURCE_INDEX), None)
    dest_router = next((r for r in routers if r.router_id == DESTINATION_INDEX), None)

    if source_router is not None:
        pygame.draw.circle(screen, RED, to_screen(source_router.coord), 9)
    if dest_router is not None:
        destination_color = BLUE
        if rate == 0.0:
            destination_color = RED
        elif rate == 1.0:
            destination_color = BLUE
        pygame.draw.circle(screen, destination_color, to_screen(dest_router.coord), 9)

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
done = False
clock = pygame.time.Clock()

# Инициализация роутеров
routers = initialize()

for rtr in routers:
    topology.add_new_node(rtr.router_id)

class Streaming:
    def __init__(self):
        self.reciever = protocol.Receiver(WINDOW_SIZE)
        self.sender = protocol.Sender(WINDOW_SIZE, PACKAGE, TIMEOUT)

    def progress(self):
        if self.sender.is_done():
            return 1.0
        return self.sender.ans_count / (self.sender.max_number + 1)

    def send_msg(self):
        if self.sender.send_msg_queue.has_msg():
            self.reciever.recieve_msg_queue.send_message(self.sender.send_msg_queue.get_message())
        if self.reciever.send_msg_queue.has_msg():
            self.sender.recieve_msg_queue.send_message(self.reciever.send_msg_queue.get_message())

    def update(self):
        self.sender.update()
        self.reciever.update()

stream = Streaming()
prev_path = []

while not done:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            done = True

    connections, path, rate = step(routers)
    render(screen, routers, connections, path, rate)

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()