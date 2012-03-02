import dnslib

data = "be63010000010000000000000279610272750000010001".decode("hex")
q = dnslib.DNSRecord.parse(data)
r=q.reply(data='127.0.0.1')
r.add_answer(dnslib.RR(rtype=1, rclass=1, ttl=600, rdata='127.0.0.1'))


print r.pack()
