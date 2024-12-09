from typing import List
from matplotlib import pyplot as plt
from network import Network, Point


def img_save_dst() -> str:
    return 'img/'


class Plotter:
    def __init__(self) -> None:
        pass
    
    
    def plot_points(self, points: List[Point], show: bool = True, title: str = '') -> None:
        xs = [p.x for p in points]
        ys = [p.y for p in points]
        plt.plot(xs, ys, 'o')

        for i, p in enumerate(points):
            plt.text(p.x, p.y + 0.05, f'{i}')

        if show:
            plt.savefig(f'{img_save_dst()}{title}.png', dpi=200)
            plt.clf()

    def plot_network_grapth(self, network: Network, title: str = '') -> None:
        for i, neightbours in enumerate(network.nodes_graph):
            cur_point = network.nodes[i]

            for node_idx in neightbours:
                neightbour_point = network.nodes[node_idx]
                plt.plot((cur_point.x, neightbour_point.x), (cur_point.y, neightbour_point.y), 'r')

        self.plot_points(network.nodes, False)
        plt.savefig(f'{img_save_dst()}{title}.png', dpi=200)
        plt.clf()