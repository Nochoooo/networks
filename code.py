import numpy as np
import enum
import time
from threading import Thread
import matplotlib.pyplot as plt


class MsgStatus(enum.Enum):
    SUCCESS = enum.auto()
    FAILED = enum.auto()


class Packet:
    idx = -1
    true_idx = -1
    content = ""
    status = MsgStatus.SUCCESS

    def __init__(self):
        pass

    def clone(self):
        packet = Packet()
        packet.idx = self.idx
        packet.content = self.content
        packet.status = self.status

    def __str__(self):
        return f"({self.true_idx}({self.idx}), {self.content}, {self.status})"


class PacketBuffer:
    def __init__(self, failure_rate=0.3):
        self.buffer = []
        self.failure_rate = failure_rate

    def has_packet(self):
        return len(self.buffer) > 0

    def retrieve_packet(self):
        if self.has_packet():
            packet = self.buffer[0]
            self.buffer.pop(0)
            return packet

    def add_packet(self, packet):
        problematic_packet = self.simulate_errors(packet)
        self.buffer.append(problematic_packet)

    def simulate_errors(self, packet):
        if np.random.rand() <= self.failure_rate:
            packet.status = MsgStatus.FAILED
        return packet

    def __str__(self):
        return "[ " + ", ".join(f"({p.idx}, {p.status})" for p in self.buffer) + " ]"


def go_back_n_sender(window, limit, timeout):
    seq_num = 0
    ack_num = -1
    last_time = time.time()
    while ack_num < limit:
        next_seq = (ack_num + 1) % window

        if ack_queue.has_packet():
            ack = ack_queue.retrieve_packet()
            if ack.idx == next_seq:
                ack_num += 1
                last_time = time.time()
            else:
                seq_num = ack_num + 1

        if time.time() - last_time > timeout:
            seq_num = ack_num + 1
            last_time = time.time()

        if (seq_num < ack_num + window) and (seq_num <= limit):
            msg_seq = seq_num % window
            packet = Packet()
            packet.idx = msg_seq
            packet.true_idx = seq_num
            msg_queue.add_packet(packet)
            sent_packets.append(f"{seq_num}({msg_seq})")
            seq_num += 1

    packet = Packet()
    packet.content = "STOP"
    msg_queue.add_packet(packet)


def go_back_n_receiver(window):
    expected_seq = 0
    while True:
        if msg_queue.has_packet():
            packet = msg_queue.retrieve_packet()
            if packet.content == "STOP":
                break
            if packet.status == MsgStatus.FAILED:
                continue
            if packet.idx == expected_seq:
                ack = Packet()
                ack.idx = packet.idx
                ack_queue.add_packet(ack)
                received_packets.append(f"{packet.true_idx}({packet.idx})")
                expected_seq = (expected_seq + 1) % window


def selective_repeat_sender(window, limit, timeout):
    class PacketState(enum.Enum):
        ACTIVE = enum.auto()
        RETRANSMIT = enum.auto()
        AVAILABLE = enum.auto()

    class WindowSlot:
        def __init__(self, idx):
            self.state = PacketState.RETRANSMIT
            self.timestamp = 0
            self.idx = idx

        def __str__(self):
            return f"( {self.idx}, {self.state}, {self.timestamp})"

    window_slots = [WindowSlot(i) for i in range(window)]
    ack_count = 0

    while ack_count < limit:
        slot_info = "[" + "".join([str(slot) for slot in window_slots]) + "]"
        if ack_queue.has_packet():
            ack = ack_queue.retrieve_packet()
            ack_count += 1
            window_slots[ack.idx].state = PacketState.AVAILABLE

        current_time = time.time()
        for slot in window_slots:
            if slot.idx > limit:
                continue
            if current_time - slot.timestamp > timeout:
                slot.state = PacketState.RETRANSMIT

        for slot in window_slots:
            if slot.idx > limit:
                continue
            if slot.state == PacketState.ACTIVE:
                continue
            elif slot.state == PacketState.RETRANSMIT:
                slot.state = PacketState.ACTIVE
                slot.timestamp = time.time()
                packet = Packet()
                packet.idx = window_slots.index(slot)
                packet.true_idx = slot.idx
                msg_queue.add_packet(packet)
                sent_packets.append(f"{packet.true_idx}({packet.idx})")
            elif slot.state == PacketState.AVAILABLE:
                slot.state = PacketState.ACTIVE
                slot.timestamp = time.time()
                slot.idx += window
                if slot.idx > limit:
                    continue
                packet = Packet()
                packet.idx = window_slots.index(slot)
                packet.true_idx = slot.idx
                msg_queue.add_packet(packet)
                sent_packets.append(f"{packet.true_idx}({packet.idx})")

    packet = Packet()
    packet.content = "STOP"
    msg_queue.add_packet(packet)


def selective_repeat_receiver(window):
    while True:
        if msg_queue.has_packet():
            packet = msg_queue.retrieve_packet()
            if packet.content == "STOP":
                break
            if packet.status == MsgStatus.FAILED:
                continue
            ack = Packet()
            ack.idx = packet.idx
            ack_queue.add_packet(ack)
            received_packets.append(f"{packet.true_idx}({packet.idx})")


msg_queue = PacketBuffer()
ack_queue = PacketBuffer()

sent_packets = []
received_packets = []


def loss_test():
    global msg_queue
    global ack_queue
    global sent_packets
    global received_packets

    window = 3
    timeout = 0.2
    max_seq = 100
    loss_rates = np.linspace(0, 0.9, 9)
    protocols = ["GBN", "SRP"]

    print("p    | GBN             |SRP")
    print("     | t     |k      |t    |  k")

    gbn_times = []
    srp_times = []
    gbn_efficiency = []
    srp_efficiency = []

    for loss_prob in loss_rates:
        row = f"{loss_prob:.1f}\t"
        msg_queue = PacketBuffer(loss_prob)
        ack_queue = PacketBuffer(loss_prob)
        sent_packets = []
        received_packets = []

        for protocol in protocols:
            if protocol == "GBN":
                sender_thread = Thread(target=go_back_n_sender, args=(window, max_seq, timeout))
                receiver_thread = Thread(target=go_back_n_receiver, args=(window,))
            elif protocol == "SRP":
                sender_thread = Thread(target=selective_repeat_sender, args=(window, max_seq, timeout))
                receiver_thread = Thread(target=selective_repeat_receiver, args=(window,))

            start = time.time()
            sender_thread.start()
            receiver_thread.start()
            sender_thread.join()
            receiver_thread.join()
            end = time.time()

            efficiency = len(received_packets) / len(sent_packets)
            elapsed_time = end - start
            row += f" | {elapsed_time:.2f}  | {efficiency:.2f}   "

            if protocol == "GBN":
                gbn_times.append(elapsed_time)
                gbn_efficiency.append(efficiency)
            else:
                srp_times.append(elapsed_time)
                srp_efficiency.append(efficiency)

        print(row)

    fig, ax = plt.subplots()
    ax.plot(loss_rates, gbn_efficiency, label="Go-Back-N")
    ax.plot(loss_rates, srp_efficiency, label="Selective Repeat")
    ax.set_xlabel('Packet loss probability')
    ax.set_ylabel('Efficiency')
    ax.legend()
    ax.grid()
    fig.show()

    fig, ax = plt.subplots()
    ax.plot(loss_rates, gbn_times, label="Go-Back-N")
    ax.plot(loss_rates, srp_times, label="Selective Repeat")
    ax.set_xlabel('Packet loss probability')
    ax.set_ylabel('Transmission time (s)')
    ax.legend()
    ax.grid()
    fig.show()


def window_size_test():
    global msg_queue
    global ack_queue
    global sent_packets
    global received_packets

    window_sizes = range(2, 11)
    timeout = 0.2
    max_seq = 100
    loss_prob = 0.2
    protocols = ["GBN", "SRP"]

    print("w    | GBN             |SRP")
    print("     | t     |k      |t    |  k")

    gbn_times = []
    srp_times = []
    gbn_efficiency = []
    srp_efficiency = []

    for window in window_sizes:
        row = f"{window:}\t"
        msg_queue = PacketBuffer(loss_prob)
        ack_queue = PacketBuffer(loss_prob)
        sent_packets = []
        received_packets = []

        for protocol in protocols:
            if protocol == "GBN":
                sender_thread = Thread(target=go_back_n_sender, args=(window, max_seq, timeout))
                receiver_thread = Thread(target=go_back_n_receiver, args=(window,))
            elif protocol == "SRP":
                sender_thread = Thread(target=selective_repeat_sender, args=(window, max_seq, timeout))
                receiver_thread = Thread(target=selective_repeat_receiver, args=(window,))

            start = time.time()
            sender_thread.start()
            receiver_thread.start()
            sender_thread.join()
            receiver_thread.join()
            end = time.time()

            efficiency = len(received_packets) / len(sent_packets)
            elapsed_time = end - start
            row += f" | {elapsed_time:.2f}  | {efficiency:.2f}   "

            if protocol == "GBN":
                gbn_times.append(elapsed_time)
                gbn_efficiency.append(efficiency)
            else:
                srp_times.append(elapsed_time)
                srp_efficiency.append(efficiency)

        print(row)

    fig, ax = plt.subplots()
    ax.plot(window_sizes, gbn_efficiency, label="Go-Back-N")
    ax.plot(window_sizes, srp_efficiency, label="Selective Repeat")
    ax.set_xlabel('Window size')
    ax.set_ylabel('Efficiency')
    ax.legend()
    ax.grid()
    fig.show()

    fig, ax = plt.subplots()
    ax.plot(window_sizes, gbn_times, label="Go-Back-N")
    ax.plot(window_sizes, srp_times, label="Selective Repeat")
    ax.set_xlabel('Window size')
    ax.set_ylabel('Transmission time (s)')
    ax.legend()
    ax.grid()
    fig.show()


if __name__ == "__main__":
    window_size_test()
    loss_test()
    plt.show()
