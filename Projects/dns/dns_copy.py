import requests, os, dns.resolver, sqlite3, time
from azure.identity import DefaultAzureCredential
from azure.mgmt.dns import DnsManagementClient
from dotenv import load_dotenv

load_dotenv()
technitium_api_token = os.getenv("technitium_api_token")
subscription_id = os.getenv("subscription_id")

# SQLITE DB SETUP
con = sqlite3.connect("/home/mpopov/testrepo/Projects/dns/bla.db")
cur = con.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS azure (
    record_fqdn TEXT,
    record_type TEXT,
    record_value TEXT,
    UNIQUE(record_fqdn, record_type, record_value)
)
""")

# DNS RESOLVER
custom_resolver = dns.resolver.Resolver()

def get_azure_records(resource_group_name, zone_name):
    """get iterable object containing record sets from a zone from Azure"""
    dns_client = DnsManagementClient(DefaultAzureCredential(), subscription_id)
    record_sets = dns_client.record_sets.list_by_dns_zone(
        resource_group_name=resource_group_name,
        zone_name=zone_name
        )
    return record_sets

def get_technitium_records(zone):
    params = {
            "token": technitium_api_token,
            'domain':zone,
            'listZone':True
    }
    return requests.get(url_get,params=params).json()

class Record:
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
            self.record_value.sort()

    def add_record_to_table(self,table_name,record_fqdn,record_type,record_value):
        cur.executemany(
            f"""
            INSERT OR IGNORE INTO {table_name} (record_fqdn, record_type, record_value)
            VALUES (?, ?, ?)
            """, 
            [
                (record_fqdn, record_type, value)
                for value in record_value
            ]
        )
        con.commit()

    def del_record_from_table(self,table_name,record_fqdn,record_type,record_value):
        cur.executemany(
            f"""
            DELETE FROM {table_name}
            WHERE record_fqdn = ?
            AND record_type = ?
            AND record_value = ?
            """, 
            [
                (record_fqdn, record_type, value)
                for value in record_value
            ]
            )
        con.commit()

    def record_exists_in_table(self, table_name, record_fqdn, record_type, record_value):
        for value in record_value:
            cur.execute(
                f"""
                SELECT 1
                FROM {table_name}
                WHERE record_fqdn = ?
                AND record_type = ?
                AND record_value = ?
                LIMIT 1
                """,
                (record_fqdn, record_type, value)
            )

            if cur.fetchone() is None:
                return False
        return True
    
    def add_values_to_technitium(self):
        for value in self.record_value:
            self.build_params(value)
            self.add_record_to_technitium()

    def del_values_from_technitium(self):
        for value in self.record_value:
            self.build_params(value)
            self.del_record_from_technitium()

    def add_record_to_technitium(self):
        response = requests.get(url_add, params=self.params)
        if not response.ok:
            print(f"failed to add {self.record_fqdn} to technitium")

    def del_record_from_technitium(self):
        print(f"Attempting to delete record: {self.record_fqdn}")
        response = requests.get(url_del, params=self.params)
        if not response.ok:
            print(f"failed to delete {self.record_fqdn} from technitium")

class A(Record):
    def build_params(self,record_value):
        self.params["ipAddress"] = record_value

class CNAME(Record):
    def build_params(self,record_value):
        self.params["cname"] = record_value

class TXT(Record):
    def format_oversized_txt_value(self,value):
        """
        DNSPython separates < 255 byte record values with ...gWe" "vE0...
        Technitium does not accept record values > 255 bytes unless seperated by \n
        """
        value = value.strip('"')
        value = value.replace('" "',"\n")
        return(value)

    def build_params(self,record_values):
        """'Values' is a concatenation of values with '\n'.
        '\n' splits TXT record values for Technitium"""
        values = ""
        for record_value in record_values:
            value = record_value.strip('"')
            if len(value) > 255:
                values += self.format_oversized_txt_value(value)
            else:
                values += value + ("\n")

        self.params["text"] = values
        self.params["splitText"] = "true"

    def get_record_value(self,nameserver):
        """dnsPython and txt records require somewhat complex normalization"""
        custom_resolver.nameservers = [nameserver]
        try:
            answer = custom_resolver.resolve(self.record_fqdn, self.record_type)
        except (dns.resolver.NoNameservers, dns.resolver.NoAnswer) as e:
            print(f"lookup failed: {self.record_fqdn} {self.record_type}: {type(e).__name__}")
            return
        for value in answer:
            if '" "' in value.to_text(): # dnspython txt record, split into list
                self.record_value = value.to_text().split('" "')
            else:
                self.record_value.append(value.to_text())
        for index, value in enumerate(self.record_value):
            self.record_value[index] = value.strip('"')
        self.record_value.sort()

    def add_values_to_technitium(self):
        self.build_params(self.record_value)
        self.add_record_to_technitium()

    def del_values_from_technitium(self):
        self.build_params(self.record_value)
        self.del_record_from_technitium()

class CAA(Record):
    def build_params(self,record_value):
        flags, tag, value = record_value.split()
        self.params['flags'] = flags
        self.params['tag'] = tag
        self.params['value'] = value

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
        for index, value in enumerate(self.record_value):
            self.record_value[index] = value.replace('"',"")
        self.record_value.sort()

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

def main():
    global zone, resource_group_name, url_add, url_get, url_del
    zone = "kenwavesolutions.com"
    resource_group_name = "Pipesonik_Resources"
    technitium_ip = "192.168.88.2"
    url_add = f"http://{technitium_ip}:5380/api/zones/records/add"
    url_get = f"http://{technitium_ip}:5380/api/zones/records/get"
    url_del = f"http://{technitium_ip}:5380/api/zones/records/delete"

    RECORD_CLASSES = { "A": A, "CNAME": CNAME, "TXT": TXT, "CAA": CAA, "SRV": SRV, "MX": MX,}

    loop = 0
    while True:

        cur.execute("DELETE FROM azure")
        con.commit()
        azure_records = get_azure_records(resource_group_name,zone)
        for record in azure_records:
            record_type = record.type.split("/")[-1]
            record_fqdn = record.fqdn.strip(".")
            record_class = RECORD_CLASSES.get(record_type)
            if record_class is None:
                continue

            new_record = record_class(record_type,record_fqdn)
            new_record.get_record_value("8.8.8.8")
            new_record.add_record_to_table("azure",new_record.record_fqdn,new_record.record_type,new_record.record_value)
            new_record.add_values_to_technitium()


        technitium_records = get_technitium_records(zone)

        for record in technitium_records["response"]["records"]:
            record_type = record['type']
            record_fqdn = record['name']
            record_class = RECORD_CLASSES.get(record_type)
            if record_class is None:
                continue
            
            new_record = record_class(record_type,record_fqdn)
            new_record.get_record_value("192.168.88.2")
            if new_record.record_exists_in_table("azure", new_record.record_fqdn, new_record.record_type, new_record.record_value):
                new_record.add_values_to_technitium()
            else:
                new_record.del_values_from_technitium()
                
        loop += 1
        print(f"loop number {loop} completed")
        time.sleep(10)
main()