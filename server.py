#!/usr/bin/env python

import os
import sys
import Queue
import socket
import threading
from time import sleep
from construct.protocols.application.dns import dns
from construct import Container
from abstractbackend import abstract_backend

class udp_worker(threading.Thread):
    def __init__(self, dispatcher, queue, group=None, target=None, name=None, args=(), kwargs={}):
        threading.Thread.__init__(self, group=None, target=None, name=None, args=(), kwargs={})
        self.d = dispatcher
        self.q = queue
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def run(self):
        while not self.d.shutting_down:
            try:
                data, addr, s = self.q.get(True, 1)
            except Queue.Empty:
                # This is to ensure we won't block forever
                continue
            try:
                self.process(data, addr, s)
            except:
                # some error handling would be great
                raise
            finally:
                # remove task anyway
                self.q.task_done()

    def process(self, data, addr, s):
        try:
            d = dns.parse(data)
        except:
            # could not properly parse, so just fail
            print "could not parse request"
            return
        questions = list()
        for q in d.questions:
            questions.append( (q.type, q.name, q['class']) )
        try:
            err, answer, authority, additional = self.d.backend.get_result(questions)
        except:
            err = 2
            answer = list()
            authority = list()
            additional = list()
            print "error getting result from backend"
        a = self.build_answer(d, err, answer, authority, additional)
        self.respond(addr, a, s)

    def build_answer(self, d, err, answer, authority, additional):
        # Construct answer
        # answer section
        answers = list()
        for ans in answer:
            print ans
            i = Container()
            for prop in ('type', 'name', 'class', 'ttl', 'rdata'): 
                print prop
                i[prop] = ans[prop]
            answers.append(i)
        # authority section
        authorities = Container()
        for authr in authority:
            i = Container()
            for prop in ['type', 'name', 'class', 'ttl', 'rdata']: i[prop] = authr[prop]
            authorities.append(i)
        # additional section
        additionals = Container()
        for addtl in additional:
            i = Container()
            for prop in ['type', 'name', 'class', 'ttl', 'rdata']: i[prop] = addtl[prop]
            additionals.append(i)

        # flags
        f = Container(
                       recursion_available = False,
                       recurssion_desired = False,
                       response_code = err,
                       authenticated_data = False,
                       authoritive_answer = len(authority)>0,
                       opcode = d.flags.opcode,
                       checking_disabled = False,
                       truncation = False,
                       type = 'RESPONSE'
                      )
           
        a = Container(
                       additional_count = len(additional),
                       answer_count = len(answer),
                       authority_count = len(authority),
                       id = d.id,
                       question_count = 0,
                       flags = f,
                       additionals = additionals,
                       answers = answers,
                       authorities = authorities,
                       questions = [],
                     )
        return dns.build(a)

    def respond(self, addr, data, s):
        s.sendto(data, addr)

class udp_dispatcher(threading.Thread):
    def __init__(self, queue, backend, min_threads=1, max_threads=0, start_threads=5, group=None, target=None, name=None, args=(), kwargs={}):
        threading.Thread.__init__(self, group=None, target=None, name=None, args=(), kwargs={})
        self.daemon = True
        self.q = queue
        self.max_threads = max_threads
        self.min_threads = min_threads
        self.start_threads = start_threads
        self.workers = list()
        self.worker_class = udp_worker
        self.backend = backend
        self.shutting_down = False
        self.down = False
        for i in range(start_threads): self.start_worker()

    def start_worker(self):
        t = self.worker_class(self, self.q, self.backend)
        self.workers.append(t)
        t.start()

    def shutdown(self):
        self.shutting_down = True
        for w in self.workers:
            w.join()
        self.down = True

    def run(self):
        while not self.down: sleep(1)

if __name__=="__main__":
    q = Queue.Queue()
    ud = udp_dispatcher(q, abstract_backend())
    ud.start()
    host, port = '', 53
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((host, port))
    while True:
        try:
            # we'll read datagram right in the main loop,
            # hopefully it's fast enough, but have to test later
            # DNS Datagram can not be over 512 bytes
            data, addr = s.recvfrom(512)
            # put datagram to queue
            q.put((data, addr, s))
        except KeyboardInterrupt:
            print "Waiting for queue to be processed"
            ud.shutdown()
            q.join()
            print "Bye-bye!"
            sys.exit(0)
