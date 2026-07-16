import sys, requests, socket, os, dns.resolver
from azure.identity import DefaultAzureCredential
from azure.mgmt.dns import DnsManagementClient
from dotenv import load_dotenv
load_dotenv()
technitium_api_token = os.getenv("technitium_api_token")
subscription_id = os.getenv("subscription_id")
rdict = {}

def get_azure_records(resource_group_name: str, zone_name: str):
    dns_client = DnsManagementClient(DefaultAzureCredential(), subscription_id)
    record_sets = dns_client.record_sets.list_by_dns_zone(
        resource_group_name=resource_group_name,
        zone_name=zone_name,
    )

    supported_types = ["A", "CNAME", "TXT", "CAA", "SRV", "MX"]

    for record in record_sets:
        rtype = record.type.split('/')[-1]
        print(f"{'-'*40}\n{record.fqdn}\n{rtype}")
        
        rdict[record.fqdn] = {
            'fqdn': record.fqdn,
            'type': rtype,
            'values': []
        }

        if rtype in supported_types:
            try:
                answer = dns.resolver.resolve(record.fqdn, rtype)
                for rdata in answer:
                    # to_text() automatically formats the output correctly for A, MX, TXT, etc.
                    print(rdata.to_text())
                    rdict[record.fqdn]['values'].append(rdata.to_text())
            except dns.exception.DNSException:
                pass

    print(rdict['kenwavesolutions.com.'])


def get_technitium_records():


def get_technitium_a_records():

    url = "http://192.168.88.2:5380/api/zones/records/get"
    dns_store = {}
    params = {
        "token":technitium_api_token,
        'domain':'lab.mpopov.net',
        'listZone':"true",
    }
    
    response = requests.get(url, params=params)
    
    data = response.json()
    records_list = data['response']['records']

    for record in records_list:
        if record.get('type') == 'A':
            ipaddr = record.get('rData')
            name = record.get('name').split('.')[0]
            dns_store[name] = {
                "name": name,
                "type": record.get('type'),
                "ip": ipaddr.get('ipAddress')
            }

    return(dns_store)


def add_technitium_records(RECORDS_TO_ADD):

    url = "http://192.168.88.2:5380/api/zones/records/add"
    zone = "python.com"

    for record in RECORDS_TO_ADD.values():

        params = {
            "token":technitium_api_token,
            'zone':zone,
            'domain':f"{record.get('name')}.{zone}",
            'type':'A',
            'ipAddress':record.get('ip')
        }

        response = requests.get(url, params=params)
        print(f"{record.get('name')}.{zone}")
        print(response)
    

if __name__ == "__main__":
    
    RESOURCE_GROUP = "Pipesonik_Resources" 
    ZONE_NAME = "kenwavesolutions.com"
    # RECORDS_TO_ADD = get_azure_a_records(RESOURCE_GROUP,ZONE_NAME)

    # get_technitium_a_records()
    # get_azure_a_records(RESOURCE_GROUP,ZONE_NAME)
    # add_technitium_records(RECORDS_TO_ADD)    
    get_azure_records(RESOURCE_GROUP,ZONE_NAME)