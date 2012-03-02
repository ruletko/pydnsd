

class abstract_backend(object):
    def get_result(self, questions):
        answ = list()
        for q in questions:
              answ.append( { 'type': q[0], 'class': q[2], 'name': q[1], 'ttl': 600, 'rdata': '127.0.0.1'} )
        return 0, 1, answ , list(), list()
