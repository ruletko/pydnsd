from construct.protocols.application.dns import *
from construct import *
from construct.protocols.layer3.ipv4 import IpAddressAdapter

del resource_record
del rdata

rdata = Field("data", lambda ctx: ctx.rdata_length)
resource_record = Struct("resource_record",
    CString("name", terminators = "\xc0\x00"),
    Padding(1),
    dns_record_type,
    dns_record_class,
    UBInt32("ttl"),
    UBInt16("rdata_length"),
    IfThenElse("data", lambda ctx: ctx.type == "IPv4",
        IpAddressAdapter(rdata),
        rdata
    )
  )

data = "be63010000010000000000000279610272750000010001".decode("hex")
q = dns.parse(data)
answ = { 'type': 'IPv4', 'class': 'INTERNET', 'name': 'ya.ru', 'ttl': 600, 'rdata': '127.0.0.1'}
i = Container()
for prop in ['type', 'name', 'class', 'ttl', 'rdata']:
   i[prop] = answ[prop]


#i['rdata_length'] = 
#rdata.build("abc")
resource_record.build(i)
