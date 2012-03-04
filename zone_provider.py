import dnslib

from utils.ipcalc import Network

""" notes:
     zone
        zname = str() name of zone
        views = dict("id") of qviews
     qview
        name
        id
        access = deny|allow
        iplist = list() of ips to use with access
        allow_axfr = list() of ips where  AXFR is allowed for this zone
        view_iplist = list() of ips for use with this view
"""

class zone_provider(object):
    def __init__(self, backend)
        self.backend = backend
        # todo: load zones at start
        # and zone settings too
        # rewrite methods accordingly

    def answer(self, question, qfrom):
        authoritive = 0
        error = 0
        answers = list()
        authorities = list()
        additionals = list()
        zone = self.get_zone(question.qname)
        if not zone: return error, authoritive, answers, authorities, additionals
        qview = self.calculate_view(zone.views, qfrom)
        if not qview: return error, authoritive, answers, authorities, additionals
        if (dnslib.QTYPE[question.qtype] == 'AXFR' and not self.ip_in(from, qview.allow_axfr))
             or (zone.access == 'deny' and not self.ip_in(from, qview.iplist))
             or (zone.access == 'allow' and self.ip_in(from, qview.iplist)): 
               error = 5
               return error, authoritive, answers, authorities, additionals
        answers = self.get_answers(zone, qview.id, qname=question.qname, qclass=question.qclass, qtype=question.qtype)
        authorities = self.get_authorities(zone, qview.id, qname=question.qname, qclass=question.qclass, qtype=question.qtype)
        additionals = self.get_additionals(zone, qview.id, qname=question.qname, qclass=question.qclass, qtype=question.qtype)
        if question.qclass < 255: authoritive = 1
        if not answers and authoritive: error = 3
        return error, authoritive, answers, authorities, additionals

    def get_zone(self, qname):
        labels = qname.split('.').append('.')
        for i in range(len(labels)):
            if self.backend.zone_exists(labels[i:]): 
               zone = self.backend.get_zone(labels[i:])
        return None

    def ip_in(addr, network):
        if len(network.split("/")) == 1: network += "/32"
        if addr in Network(network): return True
        return False

    def calculate_view(self, views, qfrom):
        for view in views.values():
            for network in view.view_iplist:
                if self.ip_in(gfrom, network): return view
        if 'default' in views.keys(): return views['default']
        return None

    def get_answers(self, zone, viewid, qname=None, qclass=None, qtype=None):
        out = list()
        rrs = self.backend.get_rrs(zone, viewid, qname, qclass, qtype)
        for rr in rrs:
            out.append(rr)
        return out
