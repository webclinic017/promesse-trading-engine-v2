from abc import ABCMeta, abstractmethod


class AbstractAnalytics(metaclass=ABCMeta):
    """
    Analytics is an abstract base class providing an interface for all subsequent (inherited) analytics (both dry and live).
    """

    @abstractmethod
    def balance(self):
        raise NotImplementedError('Should implement balance()')

    @abstractmethod
    def print_balance(self):
        raise NotImplementedError('Should implement print_balance()')

    @abstractmethod
    def profit(self):
        raise NotImplementedError('Should implement profit()')

    @abstractmethod
    def print_profit(self):
        raise NotImplementedError('Should implement print_profit()')

    @abstractmethod
    def performance(self):
        raise NotImplementedError('Should implement performance()')

    @abstractmethod
    def print_performance(self):
        raise NotImplementedError('Should implement print_performance()')

    @abstractmethod
    def status(self):
        raise NotImplementedError('Should implement status()')

    @abstractmethod
    def print_status(self):
        raise NotImplementedError('Should implement print_status()')

    @abstractmethod
    def daily(self, n):
        raise NotImplementedError('Should implement daily()')

    @abstractmethod
    def print_daily(self):
        raise NotImplementedError('Should implement print_daily()')
