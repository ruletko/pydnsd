

class abstract_backend(object):
    def get_result(self, questions):
        answ = { 'type': 'IPv4', 'class': 'INTERNET', 'name': 'ya.ru', 'ttl': 600, 'rdata': '127.0.0.1'}
        return 'SUCCESS', (answ, ) , list(), list()
