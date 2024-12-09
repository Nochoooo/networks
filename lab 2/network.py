from __future__ import annotations
from enum import Enum
from typing import List
from math import inf


class Topology(Enum):
    kLine = 0,
    kRing = 1,
    kStar = 2


class Point:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def dist(self, other: Point) -> float:
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5
    

def print_paths(start_node: int, paths: List[List[int]], file = None) -> None:
    for i, path in enumerate(paths):
        if len(path) > 0:
            assert path[0] == start_node
        
        if file is None:
            print(f'path {start_node} -> {i}: {path}')
        else:
            file.write(f'path {start_node} -> {i}: {path}\n')
    

class Network:
    @staticmethod
    def create_network(topology: Topology) -> Network:
        network = None

        if topology == Topology.kStar:
            nodes = [
                Point(0.0, 0.0),
                Point(1.0, 0.0), Point(0.0, 1.0), Point(-1.0, 0.0), Point(0.0, -1.0),
                Point(1.0, 1.0), Point(1.0, -1.0), Point(-1.0, 1.0), Point(-1.0, -1.0)
            ]
            network = Network(nodes=nodes, connection_radius=0.0)
            network.nodes_graph = [[0] for i, n in enumerate(nodes) if i > 0]
            network.nodes_graph = [[i for i, n in enumerate(nodes) if i > 0]] + network.nodes_graph

        return network

    def __init__(self, nodes: List[Point], connection_radius: float) -> None:
        self.nodes = nodes
        self.radius = connection_radius
        self.nodes_graph: List[List[int]] = None

    def remove_node(self, node_idx) -> None:
        self.nodes[node_idx] = Point(inf, inf)
        if self.nodes_graph is not None:
            self.build_graph()

    def build_graph(self) -> None:
        if self.nodes_graph is not None:
            return
        
        self.nodes_graph = [[i for i, n in enumerate(self.nodes) if node.dist(n) < self.radius] for node in self.nodes]

    def ospf(self, title: str) -> None:
        with open(f'results/{title}.txt', 'w') as f:
            for i in range(len(self.nodes)):
                f.write(f'Start node {i}:\n')
                paths = self.network_dijkstra(i)
                print_paths(i, paths, f)
                f.write(f'___________________________________________________\n')

    def network_dijkstra(self, start_node_idx: int) -> List[List[int]]:
        assert 0 <= start_node_idx < len(self.nodes)
        
        distances = [inf for _ in range(len(self.nodes))]
        distances[start_node_idx] = 0
        used = [False for _ in range(len(self.nodes))]
        paths = [[] for _ in range(len(self.nodes))]

        class Node:
            def __init__(self, idx: int, dist: float) -> None:
                self.vert_idx = idx
                self.dist = dist

        vertex_heap = [Node(start_node_idx, distances[start_node_idx])]

        while len(vertex_heap) > 0:
            cur_min_node = Node(-1, inf)
            cur_min_idx = -1
            for i, node in enumerate(vertex_heap):
                if node.dist < cur_min_node.dist:
                    cur_min_node = node
                    cur_min_idx= i

            del vertex_heap[cur_min_idx]
            if used[cur_min_node.vert_idx]:
                continue
            
            used[cur_min_node.vert_idx] = True

            for neightbour in self.nodes_graph[cur_min_node.vert_idx]:
                new_dist = distances[cur_min_node.vert_idx] + self.nodes[neightbour].dist(self.nodes[cur_min_node.vert_idx])
                if new_dist < distances[neightbour]:
                    distances[neightbour] = new_dist
                    vertex_heap.append(Node(neightbour, new_dist))
                    paths[neightbour] = paths[cur_min_node.vert_idx] + [cur_min_node.vert_idx]

        for i, path in enumerate(paths):
            if distances[i] < inf:
                path.append(i)

        return paths