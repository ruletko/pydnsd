#!/usr/bin/env python

import os
import sys
import Queue
import socket
import threading
import dnslib

from time import sleep
from abstractbackend import abstract_backend

QRTYPE = {
          'A':               1, # a host address
          'NS':               2, # an authoritative name server
          'MD':               3, # a mail destination (Obsolete - use MX)
          'MF':               4, # a mail forwarder (Obsolete - use MX)
          'CNAME':            5, # the canonical name for an alias
          'SOA':              6, # marks the start of a zone of authority
          'MB':               7, # a mailbox domain name (EXPERIMENTAL)
          'MG':               8, # a mail group member (EXPERIMENTAL)
          'MR':               9, # a mail rename domain name (EXPERIMENTAL)
          'NULL':             10, # a null RR (EXPERIMENTAL)
          'WKS':              11, # a well known service description
          'PTR':              12, # a domain name pointer
          'HINFO':            13, # host information
          'MINFO':            14, # mailbox or mail list information
          'MX':               15, # mail exchange
          'TXT':              16, # text strings
          'AXFR':            252, # A request for a transfer of an entire zone
          'MAILB':           253, # A request for mailbox-related records (MB, MG or MR)
          'MAILA':           254, # A request for mail agent RRs (Obsolete - see MX)
          '*':               255, # A request for all records
         }

class udp_worker(threading.Thread):
    def __init__(self, dispatcher, queue, s, group=None, target=None, name=None, args=(), kwargs={}):
        threading.Thread.__init__(self, group=None, target=None, name=None, args=(), kwargs={})
        self.d = dispatcher
        self.q = queue
        self.s = s

    def run(self):
        while not self.d.shutting_down:
            try:
                data, addr = self.q.get(True, 1)
            except Queue.Empty:
                # This is to ensure we won't block forever
                continue
            try:
                self.process(data, addr)
            except:
                # some error handling would be great
                raise
            finally:
                # remove task anyway
                self.q.task_done()

    def process(self, data, addr):
        try:
            d = dnslib.DNSRecord.parse(data)
        except:
            # could not properly parse, so just fail
            print "could not parse request"
            return
        questions = list()
        for q in d.questions:
            questions.append( (q.qtype, q.qname, q.qclass) )
        try:
            err, aa, answer, authority, additional = self.d.backend.get_result(questions)
        except:
            err = 2
            aa = 0
            answer = list()
            authority = list()
            additional = list()
            print "error getting result from backend"
        a = self.build_answer(d, err, aa, answer, authority, additional)
        self.respond(addr, a)

    def build_answer(self, d, err, aa, answer, authority, additional):
        # Construct answer
        reply = dnslib.DNSRecord(dnslib.DNSHeader(qr=1, aa=aa, rd=0, rcode=err, id=d.header.id))
        reply.questions = d.questions
        # answer section
        for rr in answer:
            print rr
            reply.add_answer(dnslib.RR(
                                         rtype=rr['type'], 
                                         rclass=rr['class'], 
                                         ttl=rr['ttl'],
                                         rname=rr['name'],
                                         rdata=dnslib.RDMAP[dnslib.QTYPE[rr['type']]](rr['rdata'])
                                      ))
        # authority section
        for rr in authority:
            reply.add_answer(dnslib.RR(
                                         rtype=rr['type'],
                                         rclass=rr['class'],
                                         ttl=rr['ttl'],
                                         rdata=rr['rdata']
                                      ))
        # additional section
        for rr in additional:
            reply.add_answer(dnslib.RR(
                                         rtype=QRTYPE[rr['type']],
                                         rclass=QRCLASS[rr['class']],
                                         ttl=rr['ttl'],
                                         rdata=rr['rdata']
                                      ))

        return reply.pack() 

    def respond(self, addr, data):
        self.s.sendto(data, addr)

class udp_dispatcher(threading.Thread):
    def __init__(self, queue, s, backend, min_threads=1, max_threads=0, start_threads=5, group=None, target=None, name=None, args=(), kwargs={}):
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
        self.s = s
        for i in range(start_threads): self.start_worker()

    def start_worker(self):
        t = self.worker_class(self, self.q, self.s, self.backend)
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
    host, port = '', 53
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((host, port))
    ud = udp_dispatcher(q, s, abstract_backend())
    ud.start()
    while True:
        try:
            # we'll read datagram right in the main loop,
            # hopefully it's fast enough, but have to test later
            # DNS Datagram can not be over 512 bytes
            data, addr = s.recvfrom(512)
            # put datagram to queue
            q.put((data, addr))
        except KeyboardInterrupt:
            print "Calling dispatcher shutdown"
            ud.shutdown()
            print "Waiting for queue to be processed"
            q.join()
            print "Bye-bye!"
            sys.exit(0)
