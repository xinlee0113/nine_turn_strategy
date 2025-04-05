from backtrader.observers import Broker


class TigerBroker(Broker):
    def __init__(self):
        print('init')