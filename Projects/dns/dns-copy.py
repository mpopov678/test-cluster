import requests, os, dns.resolver
from azure.identity import DefaultAzureCredential
from azure.mgmt.dns import DnsManagementClient
from dotenv import load_dotenv
import sqlite3

load_dotenv()
technitium_api_token = os.getenv("technitium_api_token")
subscription_id = os.getenv("subscription_id")

# SQLITE DB SETUP
con = sqlite3.connect("/home/mpopov/testrepo/Projects/dns/tutorial.db")
cur = con.cursor()
cur.execute(f"CREATE TABLE azure(record_fqdn, record_type, record_value)")
cur.execute(f"CREATE TABLE technitium(record_fqdn, record_type, record_value)")

# TECHNITIUM URL/ZONE TO ADD RECORDS
url = "http://192.168.88.2:5380/api/zones/records/add"
url2 = "http://192.168.88.2:5380/api/zones/records/get"
# USED FOR BOTH TECHNITIUM/AZURE
zone = "kenwavesolutions.com"
resource_group_name = "Pipesonik_Resources"
# DNS RESOLVER
custom_resolver = dns.resolver.Resolver()
custom_resolver.nameservers = ['8.8.8.8']

def get_azure_records(resource_group_name, zone_name):
    """get iterable object containing record sets from a zone from Azure"""
    dns_client = DnsManagementClient(DefaultAzureCredential(), subscription_id)
    record_sets = dns_client.record_sets.list_by_dns_zone(
        resource_group_name=resource_group_name,
        zone_name=zone_name
    )
    return record_sets

def get_technitium_records(zone_name):
    params = {
            "token": technitium_api_token,
            'domain':zone,
            'listZone':True
    }
    return requests.get(url2,params=params).json()

class AzureRecord:
    def __init__(self, record_type, record_fqdn):
        # record attributes
        self.record_type = record_type
        self.record_fqdn = record_fqdn
        self.record_value = []
        # record parameters for technitium
        self.params = {
            "token":technitium_api_token,
            'zone':zone,
            'domain':self.record_fqdn,
            'type':self.record_type,
        }

    def get_record_value(self,nameserver):
        """Attempts to lookup a record. If lookup fails, record is not used
        Server to be used for lookup -> custom_resolver.nameservers variable"""
        custom_resolver.nameservers = [nameserver]
        try:
            answer = custom_resolver.resolve(self.record_fqdn, self.record_type)
        except (dns.resolver.NoNameservers, dns.resolver.NoAnswer) as e:
            print(f"lookup failed: {self.record_fqdn} {self.record_type}: {type(e).__name__}")
            return
        for value in answer:
            self.record_value.append(value.to_text())

    def add_record_to_table(self,table_name):
        cur.executemany(
            f"""
            INSERT INTO {table_name} (record_fqdn, record_type, record_value)
            VALUES (?, ?, ?)
            """, 
            [
                (self.record_fqdn, self.record_type, value)
                for value in self.record_value
            ]
        )

        con.commit()


class A(AzureRecord):
    def build_params(self):
        for value in self.record_value:
            self.params["ipAddress"] = value

class CNAME(AzureRecord):
    def build_params(self):
        for value in self.record_value:
            self.params["cname"] = value

class TXT(AzureRecord):
    def format_oversized_txt_value(self,value):
        """
        DNSPython separates < 255 byte record values with ...gWe" "vE0...
        Technitium does not accept record values > 255 bytes unless seperated by \n
        """
        value = value.strip('"')
        value = value.replace('" "',"\n")
        return(value)
    
    def build_params(self):
        """'Values' is a concatenation of values with '\n'.
        '\n' splits TXT record values for Technitium"""
        values = ""
        for value in self.record_value:
            value = value.strip('"')
            if len(value) > 255:
                values += self.format_oversized_txt_value(value)
            else:
                values += value + ("\n")
        self.params["text"] = values
        self.params["splitText"] = "true"

class CAA(AzureRecord):
    """NONE in kenwavesolutions.com"""
    def build_params(self):
        flags, tag, value = self.record_value[0].split()
        self.params['flags'] = flags
        self.params['tag'] = tag
        self.params['value'] = value

class SRV(AzureRecord):
    def build_params(self):
        priority, weight, port, target = self.record_value[0].split()
        self.params['priority'] = priority
        self.params['weight'] = weight
        self.params['port'] = port
        self.params['target'] = target

class MX(AzureRecord):
    def build_params(self):
        preference, exchange = self.record_value[0].split()
        self.params['exchange'] = exchange
        self.params['preference'] = preference

def main():
    RECORD_CLASSES = {
        "A": A,
        "CNAME": CNAME,
        "TXT": TXT,
        "CAA": CAA,
        "SRV": SRV,
        "MX": MX,
    }
    azure_records = get_azure_records(resource_group_name,zone)
    for record in azure_records:
        record_type = record.type.split("/")[-1]
        record_fqdn = record.fqdn
        record_class = RECORD_CLASSES.get(record_type)
        if record_class is None:
            continue
        
        new_record = record_class(record_type,record_fqdn)
        new_record.get_record_value("8.8.8.8")
        new_record.build_params()
        new_record.add_record_to_table("azure")

    technitium_records = get_technitium_records(zone)
    for record in technitium_records["response"]["records"]:
        record_type = record['type']
        record_fqdn = record['name']
        record_class = RECORD_CLASSES.get(record_type)
        if record_class is None:
            continue

        new_record = record_class(record_type,record_fqdn)
        new_record.get_record_value("192.168.88.2")
        new_record.build_params()
        new_record.add_record_to_table("technitium")
main()

