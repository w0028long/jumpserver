from common.exceptions import JmsException


class AssetsIpsNotMatch(JmsException):
    pass


class SystemUserNotFound(JmsException):
    pass


class TicketClosed(JmsException):
    pass


class TicketActionYet(JmsException):
    pass
