import requests, os, dns.resolver, time
from azure.identity import DefaultAzureCredential
from azure.mgmt.dns import DnsManagementClient
from dotenv import load_dotenv

load_dotenv()
technitium_api_token = os.getenv("technitium_api_token")
subscription_id = os.getenv("subscription_id")

# DNS RESOLVER
custom_resolver = dns.resolver.Resolver()

def get_azure_records():
    """get iterable object containing record sets from a zone from Azure"""
    dns_client = DnsManagementClient(DefaultAzureCredential(), subscription_id)
    record_sets = dns_client.record_sets.list_by_dns_zone(
        resource_group_name=RESOURCE_GROUP_NAME,
        zone_name=ZONE
        )
    return record_sets

def get_technitium_records():
    """get dict containing all records from a zone from Technitium"""
    url_get = f"http://{TECHNITIUM_IP}:5380/api/zones/records/get"
    params = {
            "token": technitium_api_token,
            'domain':ZONE,
            'listZone':True
    }
    return requests.get(url_get,params=params).json()

class Record:
    def __init__(self, record_type, record_fqdn):
        self.record_type = record_type
        self.record_fqdn = record_fqdn
        self.record_value = []
        # record parameters for technitium
        self.params = {
            "token":technitium_api_token,
            'zone':ZONE,
            'domain':self.record_fqdn,
            'type':self.record_type,
        }

    def get_record_value(self,nameserver):
        """Retrieves record data from recordset and creates new item
        in list for each record's data."""

        custom_resolver.nameservers = [nameserver]
        try:
            answer = custom_resolver.resolve(self.record_fqdn, self.record_type)
        except (dns.resolver.NoNameservers, dns.resolver.NoAnswer) as e:
            print(f"lookup failed: {self.record_fqdn} {self.record_type}: {type(e).__name__}")
            return
        for value in answer:
            self.record_value.append(value.to_text()) # .to_text() is needed
        self.record_value.sort()
    
    def add_values_to_technitium(self):
        url_add = f"http://{TECHNITIUM_IP}:5380/api/zones/records/add"
        requests.get(url_add, params=self.params)
        print(f"adding {self.record_fqdn}")

    def del_values_from_technitium(self):
        url_del = f"http://{TECHNITIUM_IP}:5380/api/zones/records/delete"
        requests.get(url_del, params=self.params)
        print(f"deleting {self.record_fqdn}")

class A(Record):
    def build_params(self,record_value):
        self.params["ipAddress"] = record_value

class CNAME(Record):
    def build_params(self,record_value):
        self.params["cname"] = record_value

class TXT(Record):
    def build_params(self,record_value):
        self.params["splitText"] = True
        self.params["text"] = record_value

    def format_azure_record_value(self):
        """dnsPython and txt records require somewhat complex normalization"""
        for index, value in enumerate(self.record_value):
            value = value.strip('"')
            if '" "' in value: # dnspython txt record, split into list
                value = value.replace('" "', '')
            self.record_value[index] = value
        # convert list to a string
        string = "\n".join(self.record_value)

        # adding new lines after the 255 byte limit for splitText param
        value_bytes = string.encode("utf-8")
        if len(value_bytes) > 255:
            first_part = value_bytes[:255].decode("utf-8", errors="ignore")
            second_part = value_bytes[255:].decode("utf-8", errors="ignore")
            self.record_value = [f"{first_part}\n{second_part}"]
        else:
            self.record_value = [string]

    def format_technitium_record_value(self):
        for index, value in enumerate(self.record_value):
            value = value.strip('"')
            value = value.replace('" "', '\n')
            self.record_value[index] = value

    def get_record_value(self,nameserver):
        super().get_record_value(nameserver)
        if nameserver == TECHNITIUM_IP:
            self.format_technitium_record_value()
        else:
            self.format_azure_record_value()

class CAA(Record):
    def build_params(self,record_value):
        flags, tag, value = record_value.split(" ")
        self.params['flags'] = flags
        self.params['tag'] = tag
        self.params['value'] = value.strip('"')

class SRV(Record):
    def build_params(self,record_value):
        priority, weight, port, target = record_value.split()
        self.params['priority'] = priority
        self.params['weight'] = weight
        self.params['port'] = port
        self.params['target'] = target

class MX(Record):
    def build_params(self,record_value):
        preference, exchange = record_value.split()
        self.params['exchange'] = exchange
        self.params['preference'] = preference

def test_main():
    global ZONE, RESOURCE_GROUP_NAME, TECHNITIUM_IP
    ZONE = "kenwavesolutions.com"
    RESOURCE_GROUP_NAME = "Pipesonik_Resources"
    TECHNITIUM_IP = "192.168.88.2"
    RECORD_CLASSES = { "A": A, "CNAME": CNAME, "TXT": TXT, "CAA": CAA, "SRV": SRV, "MX": MX,}

    loop_count = 0

    while True:

        azure_records_now = set()
        technitium_records_now = set()
        technitium_records = get_technitium_records()
        azure_records = get_azure_records()

        # Initializing the recordsets (not a record yet)
        for record in azure_records:
            record_type = record.type.split("/")[-1]
            record_fqdn = record.fqdn.strip(".")
            record_class = RECORD_CLASSES.get(record_type)
            if record_class is None:
                continue
            else:
                new_record = record_class(record_type,record_fqdn)
            
            new_record.get_record_value("8.8.8.8") # gets recordset data, not per record

            # this for-loop processes data per record, NOT recordset like above
            for record_value in new_record.record_value:
                azure_records_now.add((record_fqdn,record_type,record_value))    

        for record in technitium_records["response"]["records"]:
            record_type = record['type']
            record_fqdn = record['name']
            record_class = RECORD_CLASSES.get(record_type)
            if record_class is None:
                continue
            else:
                new_record = record_class(record_type,record_fqdn)

            new_record.get_record_value("192.168.88.2")

            for record_value in new_record.record_value:
                technitium_records_now.add((record_fqdn,record_type,record_value))

        records_to_add = azure_records_now - technitium_records_now
        
        for record_fqdn, record_type, record_value in records_to_add:
            record_class = RECORD_CLASSES.get(record_type)
            new_record = record_class(record_type,record_fqdn)
            new_record.build_params(record_value)
            new_record.add_values_to_technitium()

        record_to_delete = technitium_records_now - azure_records_now

        for record_fqdn, record_type, record_value in record_to_delete:
            record_class = RECORD_CLASSES.get(record_type)
            new_record = record_class(record_type,record_fqdn)
            new_record.build_params(record_value)
            new_record.del_values_from_technitium()

        loop_count += 1
        print(f"Current loop count: {loop_count}")
        time.sleep(10)

test_main()