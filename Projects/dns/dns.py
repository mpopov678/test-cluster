import sys, requests, socket, os
from azure.identity import DefaultAzureCredential
from azure.mgmt.dns import DnsManagementClient

from dotenv import load_dotenv
load_dotenv()
technitium_api_token = os.getenv("technitium_api_token")
subscription_id = os.getenv("subscription_id")

def get_azure_a_records(resource_group_name: str, zone_name: str):

    dns_store = {}
    credentials = DefaultAzureCredential()
    dns_client = DnsManagementClient(credentials, subscription_id)

    record_sets = dns_client.record_sets.list_by_dns_zone(
        resource_group_name=resource_group_name,
        zone_name=zone_name,
    )

    for record in record_sets:
        if record.type.split('/')[-1] == 'A':
            try:
                ipaddr = socket.gethostbyname(record.fqdn)
            except:
                ipaddr = "n/a"
            dns_store[record.name] = {
                "name": record.name,
                "type": record.type.split('/')[-1],
                "ip": ipaddr
            }

    print(dns_store)            
    return dns_store

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
    ZONE_NAME = "infra.kenwavesolutions.com"
    RECORDS_TO_ADD = get_azure_a_records(RESOURCE_GROUP,ZONE_NAME)

    # get_technitium_a_records()
    # get_azure_a_records(RESOURCE_GROUP,ZONE_NAME)
    add_technitium_records(RECORDS_TO_ADD)    
