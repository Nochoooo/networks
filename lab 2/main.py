from typing import List
from network import Network, Point, Topology
from plot import Plotter


def main():
    plt = Plotter()

    line_topology_network = Network(
        nodes=[Point(0.0, 0.0), Point(1.0, 1.0), Point(2.0, 2.0), Point(3.0, 3.0), Point(4.0, 4.0), Point(5.0, 5.0), Point(6.0, 6.0), Point(7.0, 7.0), Point(8.0, 8.0)],
        connection_radius=1.5
    )
    line_topology_network.build_graph()
    plt.plot_network_grapth(line_topology_network, 'l_f')
    line_topology_network.ospf('l_f')

    line_topology_network.remove_node(2)
    plt.plot_network_grapth(line_topology_network, 'l_r')
    line_topology_network.ospf('l_r')

    def ring_points(r: float) -> List[Point]:
        xs = [-3.0, -2.7, -2.0, -1.0]
        xs = xs + [0.0] + [-x_k for x_k in xs]
        ys = []
        for x_k in xs:
            y_abs = (r * r - x_k * x_k) ** 0.5
            ys.extend([y_abs, -y_abs])

        points = []
        for i, x_k in enumerate(xs):
            if ys[2 * i] == 0:
                points.append(Point(x_k, ys[2 * i]))
            else:
                points.append(Point(x_k, ys[2 * i]))
                points.append(Point(x_k, ys[2 * i + 1]))
        
        return points

    ring_topology_network = Network(
        nodes=ring_points(3.0),
        connection_radius=1.7
    )
    ring_topology_network.build_graph()
    ring_topology_network.ospf('r_f')
    plt.plot_network_grapth(ring_topology_network, 'r_f')

    ring_topology_network.remove_node(5)
    ring_topology_network.ospf('r_r')
    plt.plot_network_grapth(ring_topology_network, 'r_r')

    star_topology_nerwork = Network.create_network(Topology.kStar)
    plt.plot_network_grapth(star_topology_nerwork, 's_f')
    star_topology_nerwork.ospf('s_f')

    star_topology_nerwork.remove_node(0)
    plt.plot_network_grapth(star_topology_nerwork, 's_r')
    star_topology_nerwork.ospf('s_r')


if __name__ == '__main__':
    main()